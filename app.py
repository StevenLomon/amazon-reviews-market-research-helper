import requests, re, time
import pandas as pd
import streamlit as st
from rich import print
from bs4 import BeautifulSoup, NavigableString
from datetime import datetime

# https://colab.research.google.com/drive/1pmeDcKl62fJfPBfiW_dzOz5uFsd6ptwF#scrollTo=Lof8MzzeMHkf

keyword = "pull up bar"
transformed_keyword = keyword.replace(" ", "+").strip()
amazon_url = f"https://www.amazon.com/s?k={transformed_keyword}&crid=1CCO5C5M9XGSY&sprefix={transformed_keyword}%2Caps%2C278&ref=nb_sb_noss_1"

headers = ({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36', 
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.amazon.com/',
            'DNT': '1',})

webpage = requests.get(amazon_url, headers=headers)

print(webpage)

soup = BeautifulSoup(webpage.content, parser='html.parser')
links = soup.find_all('a', attrs={'class': 'a-link-normal s-underline-text s-underline-link-text s-link-style a-text-normal'})
products = [f"https://www.amazon.com{link.get('href')}" if not link.get('href').startswith('https://') else link.get('href') for link in links]

include_four_star_reviews = False
# Create all 50 2-star review urls and all 3-star review urls
two_star_reviews_urls = []
three_star_reviews_urls = []
if include_four_star_reviews:
    four_star_reviews_urls = []

for product in products:
    product_id = re.search(r'/dp/([^/]+)', product).group(1)
    two_star_reviews_url = f"https://www.amazon.com/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_sr?ie=UTF8&filterByStar=two_star&reviewerType=all_reviews&pageNumber=1#reviews-filter-bar"
    three_star_reviews_url = f"https://www.amazon.com/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_sr?ie=UTF8&filterByStar=three_star&reviewerType=all_reviews&pageNumber=1#reviews-filter-bar"
    two_star_reviews_url.append(two_star_reviews_urls)
    three_star_reviews_urls.append(three_star_reviews_url)
    if include_four_star_reviews:
        four_star_reviews_url = f"https://www.amazon.com/product-reviews/{product_id}/ref=cm_cr_arp_d_viewopt_sr?ie=UTF8&filterByStar=four_star&reviewerType=all_reviews&pageNumber=1#reviews-filter-bar"
        four_star_reviews_urls.append(four_star_reviews_url)

def get_all_reviews_from_url_as_soups(url, headers):
    reviews_page = requests.get(url, headers=headers)
    soup = BeautifulSoup(reviews_page.content, 'html.parser')

    reviews_div = soup.find('div', attrs={'class': 'a-section a-spacing-none review-views celwidget'})
    elements_list = [child for child in reviews_div.children if not isinstance(child, NavigableString) and child.name == 'div']
    
    # Class names to check for in the last div
    pagination_class_names = set(['a-row', 'a-spacing-medium', 'a-spacing-top-extra-large-plus'])
    
    # Check if the last div is a review by inspecting its class name
    if elements_list and set(elements_list[-1].get('class', [])) & pagination_class_names == pagination_class_names:
        reviews = elements_list[:-1]  # If the last div has the pagination class, exclude it
    else:
        reviews = elements_list  # If not, include the last div
    
    return reviews

all_two_star_review_soups = []
all_three_star_review_soups = []
if include_four_star_reviews:
    all_four_star_review_soups = []

for two_star_review_url in two_star_reviews_urls:
    soup_list = get_all_reviews_from_url_as_soups(two_star_review_url, headers)
    all_two_star_review_soups.extend(soup_list)

for three_star_review_url in three_star_reviews_urls:
    soup_list = get_all_reviews_from_url_as_soups(three_star_review_url, headers)
    all_three_star_review_soups.extend(soup_list)

if include_four_star_reviews:
    for four_star_review_url in four_star_reviews_urls:
        soup_list = get_all_reviews_from_url_as_soups(four_star_review_url, headers)
        all_four_star_review_soups.extend(soup_list)

def get_title_and_url_from_soup(soup): # Since they're within the same span
    title_and_url = soup.find('a', attrs={'class': 'a-size-base a-link-normal review-title a-color-base review-title-content a-text-bold'})
    title = re.search(r'\n([^\n]+)\n', title_and_url.text).group(1)
    url = f"https://www.amazon.com{title_and_url.get('href')}"
    return (title, url)

def get_review_text_from_soup(soup):
  text = soup.find('span', attrs={'class': 'a-size-base review-text review-text-content'}).text
  text = text.replace('\n', '')
  text = text.replace('\\', '')
  return text

def get_date_and_location_from_soup(soup, store_dates_as_string):
    date_and_location = soup.find('span', attrs={'class': 'a-size-base a-color-secondary review-date'}).text
    date_as_string = re.search(r'on\s(.+)$', date_and_location).group(1)
    date = None
    if store_dates_as_string:
        date = date_as_string
    else:
        date = datetime.strptime(date_as_string, "%B %d, %Y").date()

    location = re.search(r'Reviewed in (.+?) on', date_and_location).group(1)
    location = location.capitalize().title()

    return (date, location)

def get_color_from_soup(soup):
    color = soup.find('a', attrs={'class':'a-size-mini a-link-normal a-color-secondary'}).text
    color = re.search(r'Color:\s(.+)$', color).group(1).strip()
    return color

def get_verified_status_from_soup(soup):
    verified_text = soup.find('span', attrs={'class':'a-size-mini a-color-state a-text-bold'}).text
    verified = None
    if verified_text == "Verified Purchase":
        verified = True
    else:
        verified = False
    return verified

def get_helpful_counter_from_soup(soup):
    try:
        helpful_text = soup.find('span', attrs={'class':'a-size-base a-color-tertiary cr-vote-text'}).text
        number = helpful_text.split(" ")[0]
        helpful = None
        if number == "One":
            helpful = 1
        else:
            helpful = int(number)
        return helpful
    except:
        return 0
    
reviews = {'Rating':[], 'Title':[], 'Text':[], 'URL':[], 'Date':[], 'Location':[], 'Color':[], 'Verified Purchase':[], 'Helpful counter':[]}

store_dates_as_string = True

for review_soup in all_two_star_review_soups:
    reviews['Rating'].append(2)
    reviews['Title'].append(get_title_and_url_from_soup(review_soup)[0])
    reviews['Text'].append(get_review_text_from_soup(review_soup))
    reviews['URL'].append(get_title_and_url_from_soup(review_soup)[1])
    reviews['Date'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[0])
    reviews['Location'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[1])
    reviews['Color'].append(get_color_from_soup(review_soup))
    reviews['Verified Purchase'].append(get_verified_status_from_soup(review_soup))
    reviews['Helpful counter'].append(get_helpful_counter_from_soup(review_soup))

for review_soup in all_three_star_review_soups:
    reviews['Rating'].append(3)
    reviews['Title'].append(get_title_and_url_from_soup(review_soup)[0])
    reviews['Text'].append(get_review_text_from_soup(review_soup))
    reviews['URL'].append(get_title_and_url_from_soup(review_soup)[1])
    reviews['Date'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[0])
    reviews['Location'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[1])
    reviews['Color'].append(get_color_from_soup(review_soup))
    reviews['Verified Purchase'].append(get_verified_status_from_soup(review_soup))
    reviews['Helpful counter'].append(get_helpful_counter_from_soup(review_soup))

if include_four_star_reviews:
    for review_soup in all_four_star_review_soups:
        reviews['Rating'].append(4)
        reviews['Title'].append(get_title_and_url_from_soup(review_soup)[0])
        reviews['Text'].append(get_review_text_from_soup(review_soup))
        reviews['URL'].append(get_title_and_url_from_soup(review_soup)[1])
        reviews['Date'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[0])
        reviews['Location'].append(get_date_and_location_from_soup(review_soup, store_dates_as_string)[1])
        reviews['Color'].append(get_color_from_soup(review_soup))
        reviews['Verified Purchase'].append(get_verified_status_from_soup(review_soup))
        reviews['Helpful counter'].append(get_helpful_counter_from_soup(review_soup))
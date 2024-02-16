from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import time
import pickle
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

driver = None


def scrape_airbnb_price(url, driver):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless')
        driver = webdriver.Chrome(options=options)

        driver.get(url)
        # driver.implicitly_wait(2)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        price_element = soup.find('span', {'class': '_tyxjp1'})
        price = price_element.text if price_element else 'Price not found'

        return {'Price': price}

    except Exception as e:
        return {'error': f'An error occurred: {e}'}

    finally:
        if driver:
            driver.quit()


app = Flask(__name__, static_folder='static', template_folder='templates')

def scrape_airbnb_property(url):
    try:

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        # print(response)

        soup = BeautifulSoup(response.text, 'html.parser')
        # with open('soup.pkl', 'wb') as soup_file:
        #     pickle.dump(soup, soup_file)

        result = scrape_airbnb_price(url, driver)
        price = result.get('Price', {})
        property_id = url.split('/')[-1].split('?')[0]
        property_name = soup.find('meta', property='og:description')['content']
        

        script_tag = soup.find('script', {'id': 'data-deferred-state'})
        script_content = script_tag.text if script_tag else None

        if script_content:
            json_data = json.loads(script_content)

            sections = json_data.get('niobeMinimalClientData', [])[0][1].get('data', {}).get('presentation', {}).get('stayProductDetailPage', {}).get('sections', {}).get('sections', [{}])
 
            description_section = [section for section in sections if section.get('sectionId') == 'DESCRIPTION_MODAL']
            review_section = [section for section in sections if section.get('sectionId') == 'REVIEWS_DEFAULT']
            host_section = [section for section in sections if section.get('sectionId') == 'HOST_PROFILE_DEFAULT']

            if description_section:
                description_html = description_section[0].get('section', {}).get('items', [{}])[0].get('html', {}).get('htmlText', '')
            
            if review_section:
                rating = review_section[0].get('section', {}).get('overallRating', {})
                num_reviews = review_section[0].get('section', {}).get('overallCount', {})
            
            if host_section:
                host_name = host_section[0].get('section', {}).get('title', {})

            description_text = BeautifulSoup(description_html, 'html.parser').get_text(strip=True, separator="\n")

            capacity_sections = json_data.get('niobeMinimalClientData', [])[0][1].get('data', {}).get('presentation', {}).get('stayProductDetailPage', {}).get('sections', {}).get('sbuiData', {}).get('sectionConfiguration', {}).get('root', {}).get('sections', [{}])
            capacity_section = [section for section in capacity_sections if section.get('sectionId') == 'OVERVIEW_DEFAULT_V2']

            title_values = [block.get('title', '') for block in capacity_section[0].get('sectionData').get('overviewItems')]
            capacity_info = ', '.join(title_values)

        return {
            'Property ID': property_id,
            'Property Name': property_name,
            'Caters to': capacity_info,
            'Rating': rating,
            'Number of reviews': num_reviews,
            'Host Name': host_name,
            'Price': price,
            'Description': description_text
        }
    except Exception as e:
        return {'error': str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape():
    url = request.form.get('airbnb_url')
    print(url)
    data = scrape_airbnb_property(url)
    return render_template('result.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import pandas as pd
import time
import requests
import os

# Load input data (which already contains the 'STATUS' column)
input_df = pd.read_csv('inputData.csv')

# Ensure column names are consistent
input_df.columns = [col.strip() for col in input_df.columns]

# Ensure the 'STATUS' column is of type object to store strings like 'Done', 'Not Found', or 'NOW FOUND'
input_df['STATUS'] = input_df['STATUS'].astype('object')

# Connect to the existing Chrome instance using --remote-debugging-port
chrome_options = Options()
chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
driver = webdriver.Chrome(options=chrome_options)

# Focus only on rows where 'STATUS' is some variation of 'Not Found' (case-insensitive)
for index, row in input_df[input_df['STATUS'].str.lower() == 'not found'].iterrows():
    name = row['NAME']
    location_zip = row['LOCATION_ZIP']
    location_street = row['LOCATION_STREET']
    establishment_id = row['ESTABLISHMENT_ID']

    # First attempt: search query with "facebook" appended
    search_query_facebook = f"{name} {location_street} {location_zip} facebook"
    search_query_instagram = f"{name} {location_street} {location_zip} instagram"

    print(f"\nProcessing Entry {index + 1}/{len(input_df)}")
    print(f"Search Query (Facebook): {search_query_facebook}")

    # Perform the search for Facebook
    driver.get("https://www.google.com")
    search_box = driver.find_element("name", "q")
    search_box.clear()
    search_box.send_keys(search_query_facebook)
    search_box.send_keys(Keys.RETURN)

    # Wait for results to load
    time.sleep(5)

    # Find Facebook link in the search results
    search_results = driver.find_elements("css selector", "a")
    found_facebook = False
    found_instagram = False

    for result in search_results:
        href = result.get_attribute("href")
        if href and "facebook.com" in href:
            found_facebook = href
            break

    # Try scraping Facebook profile first
    if found_facebook:
        print(f"Found Facebook link: {found_facebook}")
        driver.get(found_facebook)

        # Wait for Facebook profile page to load
        time.sleep(5)

        try:
            script = """
            const img = [...document.querySelectorAll('image')].find(img => {
                const style = window.getComputedStyle(img);
                return (style.height === '168px' && style.width === '168px') || 
                       (style.height === '152px' && style.width === '152px');
            });
            return img ? img.getAttribute('xlink:href') : null;
            """
            profile_picture_url = driver.execute_script(script)

            if profile_picture_url:
                response = requests.get(profile_picture_url)
                if not os.path.exists('collectedImages'):
                    os.makedirs('collectedImages')

                with open(f"collectedImages/{establishment_id}.jpg", "wb") as file:
                    file.write(response.content)
                
                # Update DataFrame 'STATUS' column to 'NOW FOUND'
                input_df.at[index, 'STATUS'] = 'NOW FOUND'
                input_df.to_csv('inputData.csv', index=False)  # Save to CSV after updating
                print(f"Status updated to 'NOW FOUND' for Establishment ID: {establishment_id}")

            else:
                print("Facebook profile picture not found. Retrying with Instagram...")
                input_df.at[index, 'STATUS'] = 'Not Found'
                found_facebook = False  # Retry Instagram

        except Exception as e:
            print(f"Error retrieving Facebook profile picture: {e}")
            input_df.at[index, 'STATUS'] = 'Not Found'

    # If Facebook not found or failed, try Instagram
    if not found_facebook:
        print(f"Search Query (Instagram): {search_query_instagram}")
        driver.get("https://www.google.com")
        search_box = driver.find_element("name", "q")
        search_box.clear()
        search_box.send_keys(search_query_instagram)
        search_box.send_keys(Keys.RETURN)

        # Wait for results to load
        time.sleep(5)

        # Find Instagram link in the search results
        search_results = driver.find_elements("css selector", "a")
        for result in search_results:
            href = result.get_attribute("href")
            if href and "instagram.com" in href:
                found_instagram = href
                break

        if found_instagram:
            print(f"Found Instagram link: {found_instagram}")
            driver.get(found_instagram)

            # Wait for Instagram profile page to load
            time.sleep(5)

            try:
                profile_picture_element = driver.find_element("css selector", "img[alt*='profile picture']")
                profile_picture_url = profile_picture_element.get_attribute('src')

                if profile_picture_url:
                    response = requests.get(profile_picture_url)
                    if not os.path.exists('collectedImages'):
                        os.makedirs('collectedImages')

                    with open(f"collectedImages/{establishment_id}.jpg", "wb") as file:
                        file.write(response.content)
                    
                    # Update DataFrame 'STATUS' column to 'NOW FOUND'
                    input_df.at[index, 'STATUS'] = 'NOW FOUND'
                    input_df.to_csv('inputData.csv', index=False)  # Save to CSV after updating
                    print(f"Status updated to 'NOW FOUND' for Establishment ID: {establishment_id}")
                    
                else:
                    print("Instagram profile picture not found.")
                    input_df.at[index, 'STATUS'] = 'Not Found'

            except Exception as e:
                print(f"Error retrieving Instagram profile picture: {e}")
                input_df.at[index, 'STATUS'] = 'Not Found'

    # Save the updated input data to the CSV file after each entry is processed
    input_df.to_csv('inputData.csv', index=False)
    print(f"Entry {index + 1} processed. Updated CSV saved.")

# Save the CSV once more after processing all rows
input_df.to_csv('inputData.csv', index=False)
print(f"Final CSV saved as 'inputData.csv'.")

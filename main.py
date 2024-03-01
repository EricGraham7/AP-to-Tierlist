import json
import sys
import time
import requests
import os            
import base64


"""To get the json response of the requested url."""
def jikanjson(query):
    #print("Querying for ", query)
    
    url = f'https://api.jikan.moe/v4/anime?q={query}&sfw=true'
    try:
        response = requests.get(url)
        response.raise_for_status()
        output = response.json()
        #print(output['data'][0]['title'])
        #print(output['data'][0]['images']['webp']['large_image_url'])
        return output
    except requests.exceptions.HTTPError:
        #assume it's a too many requests error and sleep - I don't want to try to figrue out how to handle all of them, but that would obviously be a good thing to do
        time.sleep(0.5)
        return jikanjson(query)  # try again


def load_json_file(file_path):
    try:
        with open(file_path, 'r') as json_file:
            data = json.load(json_file)
            return data
    except FileNotFoundError:
        print("File not found.")
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON.")
        return None


def filter_anime(json_data):
    ''' Filter out anime by status. Later add functionality to make this interactive?'''
    
    #including = ["watching", "watched"]
    including = ["watched"]
    filtered = []
    
    for entry in json_data['entries']:

        if entry['status'] in including:
            
            title, status, rating = entry['name'], entry['status'], entry['rating']
            filtered.append((title, status, rating))
            
    return filtered

def format_name(name):
    sanitized_string = ""
    for char in name:
        # Check if the character is within the desired ASCII range
        if ord(char) >= 32 and ord(char) <= 126:
            sanitized_string += char
        else:
            # Replace characters outside the desired range with an empty string
            sanitized_string += ""
    
    return sanitized_string.replace(" ", "%20")

def get_all_images_urls(data):
    new_anime_data = []
    
    for anime in data:
        my_response = jikanjson(format_name(anime[0]))
        image = my_response['data'][0]['images']['webp']['large_image_url']
        new_anime_entry = anime + (image,)
        new_anime_data.append(new_anime_entry)
        
    return new_anime_data

def download_images(image_list, output_dir):
    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    list_with_filename = []
    for name, status, rating, url in image_list:
        # Get the filename from the URL
        sanitized_name = name.replace('/', '_')
        filename = os.path.join(output_dir, sanitized_name + ".webp")

        # Download the image
        response = requests.get(url)
        if response.status_code == 200:
            # Save the image to a file
            with open(filename, 'wb') as f:
                f.write(response.content)
            list_with_filename.append((name, status, rating, url, filename))
        else:
            list_with_filename.append((name, status, rating, url, "unknown"))
            
    return list_with_filename

def image_to_data_url(image_path):
    with open(image_path, "rb") as img_file:
        img_data = img_file.read()
        base64_data = base64.b64encode(img_data).decode("utf-8")
        mime_type = "image/" + image_path.split(".")[-1]  # Extracting the file extension for MIME type
        return "data:{};base64,{}".format(mime_type, base64_data)
    
def get_Data_URLs(data):
    final_list = []
    for name, status, rating, url, location in data:
        final_list.append((name, status, rating, image_to_data_url(location)))
    return final_list
    
def export_as_json(input_data):
    my_data = {'title': 'My TierList',
        'rows': [{'name': 'S', 'imgs': []},
        {'name': 'A', 'imgs': []},
        {'name': 'B', 'imgs': []},
        {'name': 'C', 'imgs': []},
        {'name': 'D', 'imgs': []},
        {'name': 'E', 'imgs': []},
        {'name': 'F', 'imgs': []}],
        'untiered': []}
    
    all_data_urls = []
    for name, status, rating, data_URL in input_data:
        all_data_urls.append(data_URL)
        
    my_data['untiered'].extend(all_data_urls)
    
    filename = "AP_to_tierlist_export.json"
    
    with open(filename, "w") as json_file:
        json.dump(my_data, json_file, indent=4)
    return my_data


#main:
json_data = load_json_file("mylist.json")
print("Anime Planet export loaded")

filtered = filter_anime(json_data)
print("Successfully filtered anime")

full_data = get_all_images_urls(filtered)
print("Obtained image links via Jikan API")

actually_full_data = download_images(full_data, output_dir="images")
print("Downloaded images to local directory")

actually_full_data = get_Data_URLs(actually_full_data)
print("Converted images to Data URL")

actually_full_data = export_as_json(actually_full_data)
print("Successfully exported as .json file to load into Tiers Master")
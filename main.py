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

def get_user_filters():
    including = ["watched", "watching", "want to watch", "stalled", "dropped"]
    
    print("Enter the numbers of the statuses you want to keep (comma-separated, e.g., 1,2) ")
    print("[1: watched, 2: watching, 3: want to watch, 4: stalled, 5: dropped]")
    print("Or press enter for default: watched only")
    
    keep_indices = input()
    
    if keep_indices:
        try:
            keep_indices = [int(index.strip())-1 for index in keep_indices.split(",")]
            # Remove the specified indices from the list
            including = [item for index, item in enumerate(including) if index in keep_indices]
            
        except ValueError:
            print("Invalid input. Please enter comma-separated indices.")
            return get_user_filters()
    else:
        #print("Default action")
        keep_indices = "0"
        keep_indices = [int(index.strip()) for index in keep_indices.split(",")]
        # Remove the specified indices from the list
        including = [item for index, item in enumerate(including) if index in keep_indices]
    
    print("-- Keeping only:", including)
    return including


def filter_anime(json_data):
    ''' Filter out anime by status.'''
    
    including = get_user_filters()
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

def get_user_export_choice():

    print("Enter 1 to set up the tierlist or 2 to auto-complete it")
    
    user_choice = input()
    
    if user_choice:
        try:
            if(int(user_choice) == 1):
                print("-- Will export as prepared tierlist.")
                return int(user_choice)
            elif(int(user_choice) == 2):
                print("-- Will export as auto-completed tierlist.")
                return int(user_choice)
            else:
                #retry recursively
                print("Invalid input. Please enter either 1 or 2")
                return get_user_export_choice()
            
        except ValueError:
            #retry recursively
            print("Invalid input. Please enter either 1 or 2")
            return get_user_export_choice()
    else:
        #retry recursively
        print("Invalid input. Please enter either 1 or 2")
        return get_user_export_choice()

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

def export_and_auto_complete(input_data):
    my_data = {'title': 'My TierList',
        'rows': [{'name': 'S', 'imgs': []},
        {'name': 'A', 'imgs': []},
        {'name': 'B', 'imgs': []},
        {'name': 'C', 'imgs': []},
        {'name': 'D', 'imgs': []},
        {'name': 'F', 'imgs': []}],
        'untiered': []}
    
    for name, status, rating, data_URL in input_data:
        if(rating == 5):
            my_data['rows'][0]['imgs'].append(data_URL)
        elif(rating >= 4):
            my_data['rows'][1]['imgs'].append(data_URL)
        elif(rating >= 3):
            my_data['rows'][2]['imgs'].append(data_URL)
        elif(rating >= 2):
            my_data['rows'][3]['imgs'].append(data_URL)
        elif(rating >= 1):
            my_data['rows'][4]['imgs'].append(data_URL)
        elif(rating == 0.5):
            my_data['rows'][4]['imgs'].append(data_URL)
        else:
            my_data['untiered'].append(data_URL)
    
    filename = "AUTO_AP_to_tierlist_export.json"
    
    with open(filename, "w") as json_file:
        json.dump(my_data, json_file, indent=4)
    return my_data

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <filename>")
        return 1

    filename = sys.argv[1]

    # Example usage
    json_data = load_json_file(filename)

    if json_data:
        print("Anime Planet export loaded")

        anime_data_pipe = filter_anime(json_data)
        print("Successfully filtered anime")

        export_mode = get_user_export_choice()

        anime_data_pipe = get_all_images_urls(anime_data_pipe)
        print("Obtained image links via Jikan API")

        anime_data_pipe = download_images(anime_data_pipe, output_dir="images")
        print("Downloaded images to local directory")

        anime_data_pipe = get_Data_URLs(anime_data_pipe)
        print("Converted images to Data URL")

        if(export_mode == 1):
            anime_data_pipe = export_as_json(anime_data_pipe)
        else:
            anime_data_pipe = export_and_auto_complete(anime_data_pipe)
        print("Successfully exported as .json file to load into Tiers Master")
        
        #print(json.dumps(json_data, indent=4))
    else:
        print("Failed to load JSON data.")
        
if __name__ == "__main__":
    main()

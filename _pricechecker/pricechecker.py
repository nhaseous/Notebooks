from bs4 import BeautifulSoup
import cloudscraper
import math
import pickle

# Takes a public Discogs store inventory and returns pricing information on other listings on the market.


# Classes

class formattedListings: # Formatted marketplace listings for a single release.

    def __init__(self,title,url,listings,place,total):
        self.title = title
        self.url = url
        self.listings = listings
        self.place = place
        self.total = "Total: {0}".format(total)

    def __str__(self):
        return "{0}\n{1}\n{2}\n{3}".format(self.title,self.url,self.listings,self.total)


# Helper Functions

def get_inventory(username): # Given a seller username, gets their store url and inventory count.

    URL = "https://www.discogs.com/seller/{0}/profile".format(username)
    pages = count_pages(URL)

    return parse_list(URL, pages)

def count_pages(URL): # Takes URL for a Discogs store, returns the number of pages.

    scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'windows','mobile': False})
    html = scraper.get(URL).content
    soup = BeautifulSoup(html, 'html.parser')

    inventory_size = int(soup.find(id="page_content").find("li", class_="first").find("h2").text.strip().strip("For Sale"))
    pages = math.ceil(inventory_size/250)

    return pages

def parse_list(URL, pages): # Takes URL of a store inventory, returns a list of the releases and their item ids.

    scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'windows','mobile': False})
    new_list = []

    for page in range(1, pages + 1):
        # new_URL = URL + "?&limit=250&sort=artist&sort_order=asc&page={0}".format(page)
        new_URL = URL + "?&limit=250&sort=price&sort_order=asc&page={0}".format(page)
        html = scraper.get(new_URL).content
        soup = BeautifulSoup(html, 'html.parser')

        list_items = soup.find(id="pjax_container").find("tbody").find_all("tr")
        for item in list_items:
            release = item.find("td", class_="item_description")
            title = release.find("strong").text.strip()
            item_id = release.find("a", class_="item_release_link")["href"].split("-")[0].strip("/release/")

            new_list_item = (title, item_id)
            new_list.append(new_list_item)

    return new_list

def get_listings(sorted_inventory_list, inventory_list, username, release_title, item_id): # Given username and item_id, scrapes marketplace for listings and stores them in provided list.

    scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'windows','mobile': False})
    URL = "https://www.discogs.com/sell/release/{0}?ships_from=United+States&sort=price%2Casc".format(item_id)
    html = scraper.get(URL).content
    soup = BeautifulSoup(html, 'html.parser')

    count = 0
    your_place = 0
    formatted_listings = ""

    listings = soup.find("table", class_="mpitems").find_all("tr", class_="shortcut_navigable")
    for listing in listings:
        count += 1
        if is_user(username, listing):
            formatted_listings += "{0} (You) ({1})\n".format(get_price(listing), count)
            your_place = count
        else:
            if check_scam(listing):
                formatted_listings += "{0} (SCAM)\n".format(get_price(listing))
            else:
                formatted_listings += "{0}\n".format(get_price(listing))

    total = (soup.find("strong", class_="pagination_total").text.split(" of "))[-1]
    entry = formattedListings(release_title,URL,formatted_listings,your_place,total)

    if your_place < 10:
        (sorted_inventory_list[your_place - 1]).append(entry)
    else:
        sorted_inventory_list[9].append(entry)
    inventory_list.append(entry)

    return

def is_user(username, listing): # Checks if a marketplace listing matches the provided username.

    return listing.find(string=username)

def check_scam(listing): # Checks if a listing is a scam (has 0.0% seller rating).

    return listing.find(string="0.0%")

def get_price(listing): # Gets price provided a listing.

    try:
        item_condition = listing.find("p", class_="item_condition").text
        formatted_condition = format_condition(item_condition)

        if listing.find(string="New seller"):
            return "{0} {1} (New)".format(listing.find("span", class_="converted_price").text.strip(), formatted_condition)
        else:
            return "{0} {1}".format(listing.find("span", class_="converted_price").text.strip(), formatted_condition)
    except AttributeError:
        return "n/a"

def format_condition(item_condition): # Formats the item condition to (Media/Sleeve).

    media = (item_condition.split("("))[1].split(")")[0]
    try:
        sleeve = (item_condition.split("("))[2].split(")")[0]
    except IndexError:
        return "({0})".format(media.split(" or")[0])

    media = media.split(" or")[0]
    sleeve = sleeve.split(" or")[0]

    return "({0}/{1})".format(media, sleeve)

def print_sorted_list(sorted_inventory_list): # Given a sorted inventory list, prints it out.

    count = 0
    for index in range(len(sorted_inventory_list)):

        if sorted_inventory_list[index]:
            print("({0}) Count: {1}\n".format(index+1, len(sorted_inventory_list[index])))

        for entry in sorted_inventory_list[index]:
            count += 1
            print("({0})".format(count))
            print("{0}\n".format(entry))

        print("({0}) Count: {1}".format(index+1, len(sorted_inventory_list[index])))
        print('─' * 25)

    print("Place\n")
    for index in range(len(sorted_inventory_list)):
        print("{0}: {1}".format(index+1, len(sorted_inventory_list[index])))

def print_list(unsorted_inventory_list): # Prints unsorted inventory list.

    count = 0
    for entry in unsorted_inventory_list:
        count += 1
        print("({0})".format(count))
        print("{0}\n".format(entry))

def compare_inventory_list(inventory_list): # Compares inventory list with pickled list for changes.

    pickled_list = load_state()

    if pickled_list:
        print("Loaded saved inventory state.\n")

        if len(pickled_list) == len(inventory_list):
            for count in range(len(pickled_list)):
                pickled_entry = pickled_list[count]
                compare_entries(inventory_list, pickled_entry, count)
        else:
            print("Inventory size changed.")
        print("Finished comparison.")
    else:
        print("Nothing to load.\n")
        print_list(inventory_list)

    # save_state(inventory_list)
    # print("Saved inventory list as pickle.")

def compare_entries(inventory_list, pickled_entry, count): # Given an unpickled entry and an entry number, compares that pickled entry to the current inventory list.

    listings = inventory_list[count].listings
    pickled_listings = pickled_entry.listings
    current_place = inventory_list[count].place
    old_place = pickled_entry.place

    if listings != pickled_listings:
        print("({0})".format(count))
        print("{0}\n{1}".format(pickled_entry.title, pickled_entry.url))

        compare_listings(listings, pickled_listings)

        if current_place != old_place:
            print("Place: {0} --> {1}\n".format(old_place, current_place))

def compare_listings(current_listings, pickled_listings): # Given a list of listings, compares the current and pickled versions.

    current_list = current_listings.split("\n")
    pickled_list = pickled_listings.split("\n")

    for index in range(len(current_list)):
        try:
            current_listing = current_list[index]
            pickled_listing = pickled_list[index]

            if current_listing == pickled_listing:
                print(current_listing)
            else:
                if pickled_list[index+1] == current_list[index] or pickled_list[index+1].split("(You)")[0] == current_list[index].split("(You)")[0]:
                    print("{0} --> {1}".format(pickled_listing, "Removed"))
                    current_list.insert(index,pickled_listing)
                elif current_list[index+1] == pickled_list[index] or current_list[index+1].split("(You)")[0] == pickled_list[index].split("(You)")[0]:
                    print("{0} --> {1}".format("Inserted", current_listing))
                    pickled_list.insert(index,current_listing)
                elif ("You" in pickled_listing) and ("You" in current_listing):
                    if (pickled_listing.split("You")[0] == current_listing.split("You")[0]):
                        print("{0} --> {1}".format(pickled_listing, current_listing.split("(You) ")[-1]))
                    else:
                        print("{0} --> {1}".format(pickled_listing.split(" (You)")[0], current_listing))
                else:
                    print("{0} --> {1}".format(pickled_listing, current_listing))

        except IndexError:
            # print("Length of listings does not matched to saved listings.")
            print("{0} --> {1}".format("Inserted", current_list[index]))

def save_state(inventory_list): # Pickles an inventory list as a save state in a bin file.

    with open("state.bin", "wb") as f:
        pickle.dump(inventory_list, f)

def load_state(): # Loads a pickled inventory list from a bin file.

    with open("state.bin", "rb") as f:
        try:
            pickled_list = pickle.load(f)
            return pickled_list
        except pickle.UnpicklingError:
            return []

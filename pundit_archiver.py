#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

"""
This program archives content from political users.
"""

__author__      = "Aidan Bissell-Siders"
__version__     = "1.1"
__email__       = "a.bissell.siders@gmail.com"
__date__        = "2019-04-08"

import copy
import csv
import re
import sys

import datetime
import time

import requests
import urllib.parse
import savepagenow
import archiveis

import logging

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

import tweepy
from twitter_secrets import *

# import pyimgur
# from imgur_secrets import *

# should 

# youtube captions
# https://codereview.stackexchange.com/questions/166010/scraping-all-closed-captions-subtitles-of-a-youtubes-creators-video-library
# https://github.com/gordon8214/get-youtube-transcripts

# ("Desi-Rae X", "desiraethinking"), ("X X", "tree_of_logic")

def indexMatcher(list, match):
	# stolen from https://stackoverflow.com/questions/14849293/python-find-index-position-in-list-based-of-partial-string
	indices = [i for i, s in enumerate(list) if match in s]
	index = indices[0]
	return(index)


def csvQuickReader(filename):
	with open(filename, 'r', encoding = "utf-8") as csv_file:
		reader = csv.reader(csv_file)
		csv_data = [row for row in reader]
	return(csv_data)


def inoutCsvWriter(csv_inout, filename):
	with open(filename, 'w', newline = '', encoding = "utf-8") as csv_file:
		writer = csv.writer(csv_file)
		writer.writerows(csv_inout)


def dictlistCsvAppender(dictlist, filename):
	# csv-writable format
	zipped = zip(*[value for key, value in dictlist.items()])
	
	# write to csv
	with open(filename, 'a', newline = '', encoding = "utf-8") as csv_file:
		writer = csv.writer(csv_file)
		writer.writerows(zipped)
	
	# return a blank
	return(blankOutputheaderCreator())


def blankOutputheaderCreator():
	# timestamp,content_type,content_id,content_text,user_id,archive_web_id,archive_is_id,archive_video_id,archive_acreenshot_id
	blank = dict([("timestamp", []), ("content_type", []), ("content_id", []), ("content_text", []), ("user_id", []), ("archive_web_id", []), ("archive_is_id", []), ("archive_video_id", []), ("archive_acreenshot_id", [])])
	return(copy.deepcopy(blank))


def twitterApiCreator():
	# tweepy authorization
	auth = tweepy.OAuthHandler(twitter_consumer_key, twitter_consumer_secret)
	auth.set_access_token(twitter_access_token, twitter_access_token_secret)
	api = tweepy.API(auth)
	return(api)


def seleniumDriverCreator(adblock = True):
	global driver
	
	chrome_options = Options()
	
	chrome_options.add_argument("--headless")
	# chrome_options.add_argument("--window-size=1000x500")
	
	if adblock:
		chrome_options.add_argument("load-extension=" + r"C:\Users\theth\Google Drive\skeptic_archiver\adblock_3.10.0_0")
	
	driver = webdriver.Chrome(chrome_options=chrome_options)
	driver.create_options()
	
	time.sleep(10)
	
	return(driver)


def seleniumDriverChecker():
	try:
		driver
	except NameError:
		seleniumDriverCreator(adblock = False)


def youtubeScreenshot(target_url):
	# consider pressing 5 to get a middle view
	
	seleniumDriverChecker()
	
	driver.set_window_size(500, 1000)
	
	driver.get(target_url)
	
	more_button = driver.find_element_by_class_name("more-button")
	more_button.click()
	
	driver.save_screenshot("out.png")
	
	return("out.png")


def twitterScreenshot(target_url):
	seleniumDriverChecker()
	
	driver.set_window_size(1000, 1000)
	
	driver.get(target_url)
	
	driver.save_screenshot("out.png")
	
	return("out.png")


def imgurUpload(target_filename):
	im = pyimgur.Imgur(imgur_client_id, imgur_client_secret)
	uploaded_image = im.upload_image(target_filename, title = "")
	
	return(uploaded_image.link)
	
	# Imgur ERROR message: {'code': 500, 'message': 'Could not complete request', 'type': 'ImgurException', 'exception': []}


def twitterArchiver(users_information, saved_information_filename):
	print(f"twitterArchiver():	START")
	
	print(f"twitterArchiver():	create list of saved information")
	saved_information = csvQuickReader(saved_information_filename)
	
	print(f"twitterArchiver():	create list of already-saved twitter ids")
	archived_ids = []
	for row in saved_information:
		content_type_index = indexMatcher(blankOutputheaderCreator(), "content_type")
		if row[content_type_index] == "t":
			content_id_index = indexMatcher(blankOutputheaderCreator(), "content_id")
			archived_ids.append(int(row[content_id_index]))
	
	print(f"twitterArchiver():	creating list of real names with duplicates for each unique username")
	usernames_realnames = []
	for row in users_information:
		for item in row[1].split("|"):
			usernames_realnames.append([row[0], item])
	
	print(f"twitterArchiver():	creating twitter api instance")
	twitter_api = twitterApiCreator()
	
	print(f"twitterArchiver():	searching twitter content by username")
	for row in usernames_realnames:
		username = row[1]
		
		print(f"twitterArchiver():	started searching twitter posts of {username}")
		
		print(f"twitterArchiver():	creating blank; creating already-archived iterator; creating not-already-archived iterator")
		scraped_information = blankOutputheaderCreator()
		archived_iterator = 0
		not_archived_iterator = 0
		
		print(f"twitterArchiver():	creating iterable tweepy cursor")
		statuses = tweepy.Cursor(twitter_api.user_timeline, screen_name = username, count = 10, tweet_mode = "extended").items()
		
		print(f"twitterArchiver():	searching tweets")
		try:
			for status in statuses:
				# get tweet id
				tweet_id = status.id
				
				# if 3 pages have been skipped, break (essentially, this samples the first tweet of the first 3 returned pages)
				if False:# archived_iterator >= 2:
					print(f"twitterArchiver():	too many consecutive already-archived tweepy cursor pages, breaking")
					break
				# if first tweet id is already archived, go to next page
				if tweet_id in archived_ids:
					archived_iterator += 1
					try:
						next(statuses)
					except StopIteration:
						archived_iterator = 100
					continue
				else:
					archived_iterator = 0
				
				# try to get tweet text; else, skip
				try:
					tweet_text = status.full_text
				except:
					continue
				tweet_text = tweet_text.replace("\n", " ").replace("'", "").replace('"', "").replace(",", "").replace("  ", " ").replace("  ", " ")
				
				# if retweet, skip
				if re.search(pattern = "^RT @.+$", string = tweet_text):
					continue
				
				# add tweet information
				scraped_information["user_id"].append(username)
				scraped_information["content_id"].append(tweet_id)
				scraped_information["content_text"].append(tweet_text)
				scraped_information["content_type"].append("t")
				
				not_archived_iterator += 1
				
				# add archive information
				target_url = f"https://twitter.com/{username}/status/{tweet_id}"
				
				web_archive_url = ""
				while web_archive_url == "":
					try:
						web_archive_url = savepagenow.capture_or_cache(target_url)[0]
					except:
						time.sleep(1)
						continue
				web_archive_id = re.match(pattern = ".+/web/([0-9]+)/.+", string = web_archive_url).group(1)
				
				archive_is_url = ""
				while archive_is_url == "":
					try:
						archive_is_url = archiveis.capture(target_url)
					except:
						time.sleep(1)
						continue
				archive_is_id = re.match(pattern = "^.+//.+/(.+)$", string = archive_is_url).group(1)
				
				scraped_information["archive_web_id"].append(web_archive_id)
				scraped_information["archive_is_id"].append(archive_is_id)
				scraped_information["archive_video_id"].append("")
				scraped_information["archive_acreenshot_id"].append("") # scraped_information["imgur_url"].append(imgurUpload(twitterScreenshot(target_url)))
				
				# add checked timestamp information
				scraped_information["timestamp"].append(time.time())
				
				# add tweet to already-archived tweets
				archived_ids.append(tweet_id)
				
				if not_archived_iterator >= 10:
					print("twitterArchiver():	10 or more tweets have not been scraped, saving to csv")
					scraped_information = dictlistCsvAppender(scraped_information, saved_information_filename)
					not_archived_iterator = 0
			
			print(f"twitterArchiver():	finished searching twitter posts of {username}, saving to csv")
			scraped_information = dictlistCsvAppender(scraped_information, saved_information_filename)
		
			time.sleep(10)
		
		except tweepy.error.TweepError as e:
			string_error = str(e)
			print(f"twitterArchiver():	failed to search twitter posts of {username}, error: {string_error}")
			if re.search("status code = 401", string_error):
				print(f"twitterArchiver():	error 401, skipping user")
				continue
	
	print(f"twitterArchiver():	finished searching twitter posts, saving to csv")
	scraped_information = dictlistCsvAppender(scraped_information, saved_information_filename)
	
	print(f"twitterArchiver():	END")


def twitterChecker(users_information, saved_information_filename):
	print(f"twitterChecker():	START")
	
	print(f"twitterChecker():	create list of saved information")
	saved_information = csvQuickReader(saved_information_filename)
	
	print(f"twitterArchiver():	creating iterable tweepy cursor")
	twitter_api = twitterApiCreator()
	
	for row in saved_information:
		content_type_index = indexMatcher(blankOutputheaderCreator(), "content_type")
		content_type = row[content_type_index]
		
		if content_type == "t":
			timestamp_index = indexMatcher(blankOutputheaderCreator(), "timestamp")
			timestamp = row[timestamp_index]
			
			if timestamp != "":
				timestamp = float(timestamp)
				time_difference_hours = (time.time() - timestamp)/60/60
				
				if True: # time_difference_hours > 1:
					row[timestamp_index] = time.time()
					
					content_id_index = indexMatcher(blankOutputheaderCreator(), "content_id")
					content_id = row[content_id_index]
					
					user_id_index = indexMatcher(blankOutputheaderCreator(), "user_id")
					user_id = row[user_id_index]
					
					suspended = False
					protected = False
					
					# consider replacing this with a generic URL request, test which is faster
					status_results = twitter_api.statuses_lookup([content_id])
					
					if not status_results:
						try:
							user_results = twitter_api.get_user(screen_name = user_id)
							protected = user_results.protected
						except tweepy.error.TweepError as e:
							if re.search("suspended", str(e)):
								suspended = True
								protected = False
							else:
								print(f"twitterChecker():	unknown error:	" + str(e))
						
						if (not suspended) and (not protected):
							print(f"twitterChecker():	post {content_id} identified as deleted")
							time_deleted = datetime.datetime.now().strftime("%I%p %d-%m-%Y")
							
							row[content_type_index] = "td"
							
							archive_is_id_index = indexMatcher(blankOutputheaderCreator(), "archive_is")
							archive_is_url = "http://archive.is/" + row[archive_is_id_index]
							
							archive_web_id_index = indexMatcher(blankOutputheaderCreator(), "archive_web")
							archive_web_url = "http://web.archive.org/web/" + row[archive_web_id_index] + "/https:/twitter.com/" + user_id + "/status/" + content_id
							
							for user_row in users_information:
								if user_row[1] == user_id:
									real_id = user_row[0]
									break
							
							print(f"twitterChecker():	posting media status")
							media_status_text = f"{real_id} ({user_id}) deleted tweet {content_id} at about {time_deleted}\n\n Archived at {archive_is_url} and {archive_web_url}\n\nScreenshot below:"
							media_status = twitter_api.update_with_media(filename = twitterScreenshot(archive_is_url), status = media_status_text)
							media_status_id = media_status.id
							
							print(f"twitterChecker():	posting text status")
							content_text_index = indexMatcher(blankOutputheaderCreator(), "content_text")
							content_text = row[content_text_index]
							
							text_status_text = f"@PunditArchiver {real_id}:\n{content_text}"
							text_status = twitter_api.update_status(in_reply_to_status_id = media_status_id, status = text_status_text)
	
	print(f"twitterChecker():	finished checking tweets, saving to csv")
	inoutCsvWriter(saved_information, saved_information_filename)
	
	print(f"twitterChecker():	END")


def main():
	print(f"main():	START")
	
	print(f"main():	create lists of users")
	users_information = csvQuickReader("users.csv")
	saved_information_filename = "twitter_saved_information.csv"
	
	print(f"main():	running twitterArchiver()")
	twitterArchiver(users_information = users_information, saved_information_filename = saved_information_filename)
	
	print(f"main():	running twitterChecker()")
	# twitterChecker(users_information = users_information, saved_information_filename = saved_information_filename)
	
	print(f"main(): quitting driver")
	try:
		driver.quit()
	except:
		print(f"main(): no driver to close")
	
	print(f"main():	END")

if __name__ == "__main__":
	main()
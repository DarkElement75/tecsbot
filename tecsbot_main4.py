#TODO:
#TECSBot, Twitch Emote Chat Statistics Bot
#Made by DarkElement75, AKA Blake Edwards
"""
GUI
more channel functionality
create own commands functionality
	needs to be very user-friendly
	currently !addcom and !delcom
	need to add in ability to do <user>, reference user who wrote message.
timezone for streamer	
need to make it possible to enable/disable everything -checkboxes
need help for each command
	!help <command>
	putting it all in documentation instead of this will likely be better.
		warn about dangerous commands
	<command> will output this
allow customization of (almost?) any response to a command. Should allow default customisation but give a warning. Need reset to default as well.
different responses input for 8ball?
checkbox to enable/disable errors in chat, such as usage/have to be mod
checkbox for whispers for warning messages ie excessive use of caps warning/etc?
ban use of some emotes or all emotes <-checkbox gui option
expiration dates for repeat timers

SERVER:
how to keep permanently on, desktop is best current option, other than some form of cloud hosting/streamer hosting<-- see stackoverflow response
still cant track emotes it's not seeing, can't see them if it's not online. Permanent online is necessary for accurate emote stats.<-- ^

multi channel processing for comparison stats?
famous person has joined chat
donations <-if this isnt already done very well
hours til next strim?
score of current game/tourney/bo3/etc
song functionality
welcome newcomers
	custom message
	need to auth before getting subs
sub notifications
raffle -  expiration timer?
commercials? 
commands for mods to change game or title or other(commercials?)
social media info
repeat info, like social media info
allow users to program question responses like ALICE? <-- interesting idea for a solo channel
overall and per day -time user has watched stream
	other user tracking stuff
overrall and per day -messages of user, high score, etc
dont disable bot, only change some responses when offline stream
remember to only allow some commands to work if user is mod/owner
	different responses for mods/owners
check to make sure x!= '' is present in all the things
log/dict/array of recent commands? <-doubt this would actually help with an undo command
	do similar thing to moobot, have a chatbox of the commands said and run, without other misc messages
different levels of authority?
tecsbot moderator group?
when put online it will greet the first(?) viewer and followr on the list
more advanced !test results
how to find zalgo symbols?
figure out what to do with the other spamerino things
break out of if statement chain when there is a command found <-- may already be fixed, may bring up 2 errors on very rare occurences
excludes for "regulars" and subs
change autoreplies to commands, add variables for responses
all of spam control set on/off?
offtime - time stream has been offline
the minimum number of symbols should be disabled by default
may still be some lurking bugs from the multithreading
need to make sure it breaks out of the spam checks if it finds one so as not to do a double warning/timeout
link our access_token html file and this file 
fuck we have to subscribe to ourselves to know that this is set up correctly
need to have command to check if user is subscribed to channel 
	!subscribed /!subbed <user>
we have to have a "already timed out user" variable so that it can be checked and end the loop when it is true
repeat options
instead of just XXX_str in msg we could do XXX_str in msg[:2]/etc <--necessary for !repeat add to be fully functional
	would also save execution time

"""
#time for oauth 
	#this will allow us to get a list of subscribers
	#idk what else it does but it is how people add your app to their channel/acct
	#this also gives us the permissions to do stuff like get the sub list
import socket #imports module allowing connection to IRC
import thread, threading #imports module allowing timing functions
import sys, operator, time, urllib, json, math, os, random, unicodedata, requests, select
from datetime import datetime, timedelta

def get_json_servers():
	url = "http://tmi.twitch.tv/servers?cluster=group"
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	return data
	
bot_owner = 'darkelement75'
nick = 'tecsbot' 
ping_nick = "@%s" % nick
#for now making this whatever I input
channel = '#_tecsbot_1444071429976'
#channel = sys.argv[1]
channel_parsed = channel.replace("#", "")

pre_msg = "PRIVMSG %s :" % channel

server_json = get_json_servers()
server_arr = (server_json["servers"][0]).split(":")
server = server_arr[0]
port = int(server_arr[1])

password = 'oauth:'

queue = 13 #sets variable for anti-spam queue functionality <- dafuq is this used for

#initial connect
irc = socket.socket()
irc.connect((server, port)) #connects to the server
#sends variables for connection to twitch chat
irc.send("CAP REQ :twitch.tv/commands\r\n")
irc.send('PASS ' + password + "\r\n")
irc.send('NICK ' + nick + "\r\n")
irc.send('JOIN ' + channel + "\r\n")

#things to be input as settings
rol_chance = .5
rol_timeout= 60 #seconds
spam_cooldown = 30 #seconds
spam_timeout = 10 #seconds
emote_max = 2 #low for testing, max number of emotes allowed in a message before timing user out
#need to have different timeout durations for different types, also allow one universal timeout however.
emote_timeout_msg = "You have been timed out for sending a message that had %s emotes or more." % emote_max

#need to have 10 second warning for both of these
caps_perc_min_msg_len = 8
caps_perc_max = 60
#caps_num_max = 50


max_symbol_num = 8
min_symbol_chars = 15
max_symbol_perc = 40

min_spam_chars = 20
msg_length_max = 375

caps_timeout_msg = "You have been timed out for sending a message that had %s caps or more." % caps_perc_max
#caps_timeout_msg = "You have been timed out for sending a message that was %s% caps or more." % caps_num_max

permit_time = 30 #seconds
banphrase_timeout = 10 #seconds
link_whitelist_arr = []

vote_total = 0
'''
#this is already in channel settings
blacklist_timeout = 10 #seconds
blacklist_arr = ["belgium"]
'''
#This determines whether to do search_str == msg, or search_str in message when looking for commands
cmd_match_full = True

#initial connect

access_token = '0w9a9qhr1igy777149s66iryox6tjb'

	
def connect_channel(channel):
	irc = socket.socket()
	irc.connect((server, 6667)) #connects to the server
	#sends variables for connection to twitch chat
	irc.send('PASS ' + password + "\r\n")
	irc.send('USER ' + nick + ' 0 * :' + bot_owner + "\r\n")
	irc.send('NICK ' + nick + "\r\n")
	irc.send('JOIN ' + channel + "\r\n")

def connect_group():
	irc = socket.socket()
	irc.connect((server, port)) #connects to the server
	#sends variables for connection to twitch chat
	#/commands and /tags both work apparently, just gonna use this
	irc.send("CAP REQ :twitch.tv/commands\r\n")
	irc.send('PASS ' + password + "\r\n")
	irc.send('NICK ' + nick + "\r\n")
	irc.send('JOIN ' + channel + "\r\n")
	
def start_log(log_file_path):
	#if log file already exists, delete it and create new one.
	#need to execute this when the stream starts, should wait for get_uptime_min to be less than 1?
	if os.path.exists(log_file_path):
		os.remove(log_file_path)
	new_log_file = open(log_file_path, 'w')
	new_log_file.close	
	
def create_dict(dict, emote_file_path):
	#create dictionary of emotes and set all counts to 0
	#for some reason nothing will read any more emotes out of this file after this loop goes through each line, once.
	emotes_file = open(emote_file_path, 'r')
	#log_file = open(log_file_path, 'r')
	for emote in emotes_file:
		emote = emote.rstrip()
		dict[emote] = []
		dict[emote].append(0)
	return dict

def print_dict_by_key(dictionary):
	for key, value in sorted(dictionary.items()):
		if len(key) < 7:
			print "%s:\t\t\t%s" % (key, value[0])
		elif len(key) < 15:
			print "%s:\t\t%s" % (key, value[0])
		else:
			print "%s:\t%s" % (key, value[0])
			
def print_dict_by_value(dictionary):
	value_dict = sorted(dictionary.items(), key=operator.itemgetter(1))
	#gotta parse this way so as not to sort by keys again
	for pair in value_dict:
		key = pair[0]
		value = pair[1]
		if len(key) < 7:
			print "%s:\t\t\t%s" % (key, value[0])
		elif len(key) < 15:
			print "%s:\t\t%s" % (key, value[0])
		else:
			print "%s:\t%s" % (key, value[0])

def update_dict():
	print "Checking Logs..."
	
	log_file = open(log_file_path, 'r')
	for msg in log_file:
		emotes_file = open(emote_file_path, 'r')
		for emote in emotes_file:
			#parsing stuff
			emote = emote.rstrip()
			if msg.count(emote) != 0:
				emote_count = msg.count(emote)
				#count_dict[emote] = emote
				#needs to add to existing count
				count_dict[emote][0] += emote_count

def find_per_min(emote):
	emote_count = count_dict[emote][0]
	#this number is from the start of the program to the current time of the query, 
	#giving the amount of minutes from the start of the program.
	min = get_uptime_min()
	emote_per_min = emote_count / min
	return emote_per_min

def get_json_stream(channel_parsed):
	url = "https://api.twitch.tv/kraken/streams/%s" % channel_parsed
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	return data
	
def get_json_chatters(channel_parsed):
	url = "https://tmi.twitch.tv/group/user/%s/chatters" % channel_parsed
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	return data
	
def get_json_follows(channel_parsed):
	url = "https://api.twitch.tv/kraken/channels/%s/follows/" % channel_parsed
	response = urllib.urlopen(url)
	data = json.loads(response.read())
	return data
	
def get_json_subs(channel_parsed):	
	url = "https://api.twitch.tv/kraken/channels/%s/subscriptions" % channel_parsed
	data = requests.get(url, params={'oauth_token': access_token})
	print data.json()
	return data.json()

def get_json_sub_user(channel_parsed, user):
	url = "https://api.twitch.tv/kraken/channels/%s/subscriptions/%s" % (channel_parsed, user)
	data = requests.get(url, params={'oauth_token': access_token})
	print data.json()
	return data.json()
	
def start_commercial(length, channel_parsed):
	url = "https://api.twitch.tv/kraken/channels/%s/commercial" % channel_parsed
	data = requests.post(url, data={'oauth_token': access_token, 'length' : length})
	print data.json()
	return data.json()
	
def stream_online(channel_parsed):
	#we use this return value to trigger the loop of everything.
	channel_json = get_json_stream(channel_parsed)
	stream_status = channel_json["stream"]
	if stream_status == None:
		stream_status = False
	else:
		stream_status = True
	return stream_status
	
def get_uptime_min():
	channel_json = get_json_stream()
	#parse out unnecessary stuffs
	start_time = channel_json["stream"]["created_at"].replace("Z", "").replace("T", "-")
	#convert to datetime object
	start_time = time.strptime(start_time, "%Y-%m-%d-%H:%M:%S")
	#convert to unix time so we can calculate amount of hours and seconds it's been up, and other calculations.
	uptime = time.mktime(start_time) - 4*3600
	#subtract 4 hours from the (now unix)time, making it equal in time zones to ours,
	#then take current time and created time and get the difference.
	uptime = time.time() - uptime
	min = uptime / 60
	#return the minutes for epm calculations
	return min

def get_uptime_str():
	channel_json = get_json_stream()
	#parse out unnecessary stuffs
	start_time = channel_json["stream"]["created_at"].replace("Z", "").replace("T", "-")
	#convert to datetime object
	start_time = time.strptime(start_time, "%Y-%m-%d-%H:%M:%S")
	#convert to unix time so we can calculate amount of hours and seconds it's been up, and other calculations.
	uptime = time.mktime(start_time) - 4*3600
	#subtract 4 hours from the (now unix)time, making it equal in time zones to ours,
	#then take current time and created time and get the difference.
	uptime = time.time() - uptime
	hour = int(math.floor(uptime/3600))
	min = int(math.floor((uptime - hour *3600) / 60))
	sec = int(math.floor((uptime - hour *3600 - min*60)))
	if hour == 0 and min == 0:
		send_str = "%s@%s has been live for: %ss\r\n" % (pre_msg, channel_parsed, sec)
	elif hour == 0:
		send_str = "%s@%s has been live for: %sm %ss\r\n" % (pre_msg, channel_parsed, min, sec)
	else:
		send_str = "%s@%s has been live for: %sh %sm %ss\r\n" % (pre_msg, channel_parsed, hour, min, sec)	
	#return the string for sending
	return send_str

def get_time_return_str(time_type, time_str):
	return_str = ""
	if time_type > 0:
		return_str += " %s %s" % (time_type, time_str)
		if time_type > 1:
			return_str += "s"
		return_str += ", "
	else:
		return_str = ""
	return return_str
	
def parse_sec(sec):
	#assumes that parameter is not 0
	sec = float(sec)#just in case str is input
	hour = int(math.floor(sec/3600))
	min = int(math.floor((sec - hour *3600) / 60))
	sec = float(math.floor((sec - hour *3600 - min*60)))
	return_str = ""
	
	return_str += get_time_return_str(hour, "hour")
	return_str += get_time_return_str(min, "minute")
	return_str += get_time_return_str(sec, "second")
	if return_str.endswith(", "):
		return_str = return_str[:-2]
	return return_str
	
def is_mod(user, channel_parsed):
	channel_json = get_json_chatters(channel_parsed)
	mods_arr = channel_json["chatters"]["moderators"]
	if user == channel_parsed:
		#if the user is the streamer
		#can possibly add in new function to replace this and add for more different responses if triggered by streamer, is_owner
		#or just return a different value
		return True
	for mod in mods_arr:
		if user == mod.encode("ascii"):#sure they'll be something wrong with this
			return True
	return False

def is_streamer(user, channel_parsed):
	if user == channel_parsed:
		return True
	else:
		return False
	
def create_viewer_arr():
	channel_json = get_json_chatters(channel_parsed)
	viewer_arr = []
	for viewer in channel_json["chatters"]["viewers"]:
		viewer_arr.append(str(viewer))
	return viewer_arr
	
def new_follower(follower_arr, channel_parsed, pre_msg):
	follows_json = get_json_follows(channel_parsed)
	#need to return follower if there are any, and false if not
	if follows_json["follows"][0]["user"]["display_name"] not in follower_arr:
		#if the first is not already recorded, then new follower
		follower_arr.append(follows_json["follows"][0]["user"]["display_name"])
		send_str = "%sHello %s! Thank you for following %s's channel!\r\n" % (pre_msg, follows_json["follows"][0]["user"]["display_name"], channel_parsed)
		irc.send(send_str)
	for follower in follows_json["follows"]:
		#add all that arent already recorded
		if follower["user"]["display_name"] not in follower_arr:
			follower_arr.append(follower["user"]["display_name"])
	return follower_arr

def timeout(user, irc, pre_msg, timeout):
	send_str = "%s/timeout %s %s\r\n" % (pre_msg, user, timeout)
	print send_str
	irc.send(send_str)

	#def whisper(user, msg, irc):
	'''
	alright so we need to have it always connected to the group chat of the channel, so we make a huge function for that so that
	it always stays on it, but how can we get it to accept new data while in execution?
	
	main.py /whisper.py can have all the child processes underneath it - each child process is a channel bot,
	need to figure out how to set up the child processes stuff with rpyc, but should be able to communicate between the main and child with stdin/stdout
	main function can have exposed_send function to accept send/whisper data from the child processes/channel bots
	maybe have them hosted under localhost with rpyc so that the main/child process thing works im not sure how that whole setup works 
	main whisper bot with exposed send function -> child channel bots sending whisper data
	I think/hope we gucci now
	'''
	################33
	#need to have multithreading hooked up before this will work
	'''send_str = "%s/w %s %s\r\n" % (pre_msg, user, msg)
	print send_str
	irc.send(send_str)'''
	pass
	
def is_num(x):
	try:
		float(x)
		return True
	except ValueError:
		return False
	
def set_value(set_on, set_feature, msg_arr, irc):
		if msg_arr[2] == "on":
			set_on = True
			send_str = "%s%s turned on. You can do \"!set %s off\" to turn it off again.\r\n" % (pre_msg, set_feature.capitalize(), set_feature)
		elif msg_arr[2] == "off":
			set_on = False
			send_str = "%s%s turned off. You can do \"!set %s on\" to turn it on again.\r\n" % (pre_msg, set_feature.capitalize(), set_feature)
		else:
			#usage
			send_str = "%sUsage: \"!set %s on/off \".\r\n" % (pre_msg, set_feature)
		irc.send(send_str)
		return set_on

def create_emote_arr(emote_file_path):
	emotes_file = open(emote_file_path, 'r')		
	emote_arr = []
	for emote in emotes_file:
		emote = emote.rstrip()
		emote_arr.append(emote)
	return emote_arr

def caps_count(msg):
	caps = ''
	for letter in msg:
		if letter.isupper():
			caps+=letter
	return len(caps)

def caps_perc(msg):
	#number of caps divided by number of characters in the message
	caps = float(0)
	for letter in msg:
		if letter.isupper():
			caps+=1
	return (caps / len(msg)) * 100
	
def warn(user, msg, pre_msg, channel_parsed, irc, warn_arr, warn_duration, warn_cooldown, timeout_msg, timeout_duration):
	#function to warn if they havent already been warned, and time them out if they have.
	for warn_pair in warn_arr:
		if user == warn_pair[1]:
			#check if current time is longer than the warning duration from the last time name was entered
			current_time = time.time()
			if (current_time - warn_pair[0] <= warn_cooldown):
				#timeout user for long duration and remove from array
				timeout(user, irc, pre_msg, timeout_duration)
				warn_arr.remove(warn_pair)
				send_str = "%sNo %s allowed (%s)\r\n" % (pre_msg, timeout_msg, user.capitalize())
				irc.send(send_str)
				whisper_msg = "You were timed out for %s in %s (%s)" % (timeout_msg, channel_parsed, parse_sec(timeout_duration))
				whisper(user, whisper_msg)
				whisper_user = user
				return warn_arr
			else:
				#replace old entry with new one and send warning as well as timeout for warn_duration
				#short duration
				timeout(user, irc, pre_msg, warn_duration)
				warn_arr.remove(warn_pair)
				pair = [current_time, user]
				warn_arr.append(pair)
				send_str = "%sNo %s allowed (%s)(warning)\r\n" % (pre_msg, timeout_msg, user.capitalize())
				irc.send(send_str)
				whisper_msg = "You were timed out for %s in %s (%s, warning)" % (timeout_msg, channel_parsed, parse_sec(warn_duration))
				whisper(user, whisper_msg)				
				whisper_user = user
				return warn_arr
	else:
		#add new entry and send warning, with timeout for warn_duration
		#short duration
		timeout(user, irc, pre_msg, warn_duration)
		current_time = time.time()
		pair = [current_time, user]
		warn_arr.append(pair)
		send_str = "%sNo %s allowed (%s)(warning)\r\n" % (pre_msg, timeout_msg, user.capitalize())
		irc.send(send_str)
		whisper_msg = "You were timed out for %s in %s (%s, warning)" % (timeout_msg, channel_parsed, parse_sec(warn_duration))
		whisper(user, whisper_msg)
		whisper_user = user
		
	return warn_arr
		
def symbol_count(msg):
	reg_chars = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z','A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z','1','2','3','4','5','6','7','8','9','0',',','.',' ','\'','\"','?', ';']
	msg_symbol_count = 0
	for char in msg:
		if char not in reg_chars:
			msg_symbol_count += 1
	return msg_symbol_count		

def in_front(str, msg):
	if str in msg[:str]:
		return True
	else:
		return False

def whisper(user, msg):	
	send_str = "%s/w %s %s\r\n" % (pre_msg, user, msg)
	irc.send(send_str)

def channel_bot_start(channel):	
	channel_parsed = channel.replace("#", "")
	
	pre_msg = "PRIVMSG %s :" % channel
	#filepaths
	emote_file_path = "C:\\Users\\DarkElement\\Desktop\\Programming\\Challenges\\twitch_bot\\emotes.txt"
	log_file_path = "C:\\Users\\DarkElement\\Desktop\\Programming\\Challenges\\twitch_bot\\logs\\%s.log" % channel

	bot_owner = 'darkelement75'
	nick = 'tecsbot' 
	ping_nick = "@%s" % nick
	#for now making this whatever I input
	channel = '#darkelement75'
	#channel = sys.argv[1]
	channel_parsed = channel.replace("#", "")
	server = 'irc.twitch.tv'
	password = 'oauth:'
	
	
	irc = socket.socket()
	irc.connect((server, 6667)) #connects to the server
	#sends variables for connection to twitch chat
	irc.send('PASS ' + password + "\r\n")
	irc.send('USER ' + nick + ' 0 * :' + bot_owner + "\r\n")
	irc.send('NICK ' + nick + "\r\n")
	irc.send('JOIN ' + channel + "\r\n")
	while True:
		#beginning of main execution loop
		#will continuously check if stream is online, if it isnt then it will break from inner loop 
		#and wait in outer loop.
		if stream_online(channel_parsed) == True:	
			
			#start_log(log_file_path)
			emotes_file = open(emote_file_path, 'r')
			log_file = open(log_file_path, 'r')	

			#should delete dictionary of values when/if stream goes offline.
			count_dict = {}
			count_dict = create_dict(count_dict, emote_file_path)
			#update_dict()
			#print_dict_by_value(count_dict)
			
			#add current viewers to viewer_arr so we dont welcome everyone
			create_viewer_arr()
			#start with empty array of followers
			follower_arr = []
			viewer_arr = create_viewer_arr()
			raffle_users = []
			raffle_on = False
			msg_info_arr = []
			
			
			#vote_on = False
			permit_arr = []
			banphrase_arr = []
			ar_arr = []
			ban_emote_arr = []
			cmd_dict = {}
			emote_arr = []
			link_whitelist_arr = []
			comm_len_arr = [30, 60, 90, 120, 150, 180]
			repeat_arr = []
			
			rol_on = True
			ball_on = True
			banphrase_on = True
			autoreply_on = True
			link_whitelist_on = True
			antispam_on = True
			repeat_antispam_on = True
			emote_antispam_on = True
			caps_antispam_on = True
			fake_purge_antispam_on = True
			skincode_antispam_on = True
			long_msg_antispam_on = True
			zalgo_antispam_on = True
			symbol_antispam_on = True
			link_antispam_on = True
			long_word_antispam_on = True
			me_antispam_on = True
			ban_emote_on = True
			emote_stats_on = True
			repeat_on = True
			
			caps_warn_arr = []
			emote_warn_arr = []
			fake_purge_warn_arr = []
			skincode_warn_arr = []
			long_msg_warn_arr = []
			zalgo_warn_arr = []
			#block_warn_arr = []
			symbol_warn_arr = []
			link_warn_arr = []
			spam_warn_arr = []
			long_word_warn_arr = []
			me_warn_arr = []
			
			ban_emote_warn_arr = []
			link_whitelist_warn_arr = []
			if emote_arr == []:
				emote_arr = create_emote_arr(emote_file_path)
			if permit_arr == []:
				current_time = time.time()
				permit_pair = [current_time, nick]
				permit_arr.append(permit_pair)
				
			#need to make this off, until mod turns it on with a command
			#then it turns off again after elapsed voting time or mod ends raffle time with !winner or something so that a winner can be chosen
			#none of these declarations should be in here
			uptime_str = "!uptime"
			start_raffle_str = "!raffle start"
			join_raffle_str = "!raffle"
			end_raffle_str = "!raffle end"
			vote_str = "!vote"
			rol_cmd_str = "!roulette"
			permit_str = "!permit"
			'''permit_del_str = "!permit delete"
			permit_rem_str = "!permit remove"
			permit_list_str = "!permit list"
			permit_clr_str = "!permit clear"'''
			unpermit_str = "!unpermit"
			comm_str = "!commercial"
			
			banphrase_str = "!banphrase"
			banphrase_add_str = "!banphrase add"
			banphrase_del_str = "!banphrase delete"
			banphrase_rem_str = "!banphrase remove"
			banphrase_list_str = "!banphrase list"
			banphrase_clr_str = "!banphrase clear"
			
			test_str = "!test"
			test_reply = "Test successful."
			
			autoreply_str = "!autoreply"
			autoreply_add_str = "!autoreply add"
			autoreply_del_str = "!autoreply delete"
			autoreply_rem_str = "!autoreply remove"
			autoreply_list_str = "!autoreply list"
			autoreply_clr_str = "!autoreply clear"
			
			repeat_str = "!repeat"
			repeat_add_str = "!repeat add"
			repeat_del_str = "!repeat delete"
			repeat_rem_str = "!repeat remove"
			repeat_list_str = "!repeat list"
			repeat_clr_str = "!repeat clear"
			
			set_str = "!set"
			set_roulette_str = "!set roulette"
			set_ball_str = "!set 8ball"
			set_banphrase_str = "!set banphrase"
			set_autoreply_str = "!set autoreply"
			set_repeat_str = "!set repeat"
			
			set_antispam_str = "!set antispam"
			set_repeat_antispam_str = "!set repeat antispam"
			set_emote_antispam_str = "!set emote antispam"
			set_caps_antispam_str = "!set caps antispam"
			set_fake_purge_antispam_str = "!set fake purge antispam"
			set_skincode_antispam_str = "!set skincode antispam"
			set_long_msg_antispam_str = "!set long message antispam"
			set_zalgo_antispam_str = "!set zalgo antispam"
			set_symbol_antispam_str = "!set symbol antispam"
			set_link_antispam_str = "!set link antispam"
			set_long_word_antispam_str = "!set long word antispam"
			set_me_antispam_str = "!set me antispam"
			
			set_ban_emotes_str = "!set ban emotes"
			set_emote_stats_str = "!set emote stats"
			
			set_rol_cmd_str = "!roulette"
			set_rol_chance_str = "!roulette chance"
			
			link_whitelist_str = "!link whitelist"
			link_whitelist_add_str = "!link whitelist add"
			link_whitelist_del_str = "!link whitelist delete"
			link_whitelist_rem_str = "!link whitelist remove"
			link_whitelist_list_str = "!link whitelist list"
			link_whitelist_clr_str = "!link whitelist clear"
			
			#timeout_msg = "No <timeout_msg> allowed"
			caps_warn_duration = 1
			caps_warn_cooldown = 30
			caps_timeout_msg = "excessive use of caps"
			caps_timeout_duration = 1
			
			emote_warn_duration = 1
			emote_warn_cooldown = 30
			emote_timeout_msg = "excessive use of emotes"
			emote_timeout_duration = 600
			
			fake_purge_warn_duration = 1
			fake_purge_warn_cooldown = 30
			fake_purge_timeout_msg = "fake purges"
			fake_purge_timeout_duration = 1
			fake_purge_arr = ["<message deleted>"] #need more of these?
			
			skincode_msg = "!skincode"
			skincode_warn_duration = 1
			skincode_warn_cooldown = 30
			skincode_timeout_msg = "skin code variations"
			skincode_timeout_duration = 1
			
			long_msg_warn_duration = 1
			long_msg_warn_cooldown = 30
			long_msg_timeout_msg = "excessively long messages"
			long_msg_timeout_duration = 1
			
			zalgo_warn_duration = 1
			zalgo_warn_cooldown = 30
			zalgo_timeout_msg = "zalgo symbols"
			zalgo_timeout_duration = 1
			
			symbol_warn_duration = 1
			symbol_warn_cooldown = 30
			symbol_timeout_msg = "excessive use of symbols"
			symbol_timeout_duration = 1
			
			me_msg = "/me"
			me_warn_duration = 1
			me_warn_cooldown = 30
			me_timeout_msg = "usage of /me"
			me_timeout_duration = 1
			
			long_word_warn_duration = 1
			long_word_warn_cooldown = 30
			long_word_timeout_msg = "excessively long words"
			long_word_timeout_duration = 1
			
			link_whitelist_warn_duration = 1
			link_whitelist_warn_cooldown = 30
			link_whitelist_timeout_msg = "links"
			#######################################3
			link_whitelist_timeout_duration = 1
			######################################CHANGE THESE BACK
			
			spam_warn_duration = 1
			spam_warn_cooldown = 30
			spam_timeout_msg = "spam"
			spam_timeout_duration = 1
			
			ban_emote_warn_duration = 1
			ban_emote_warn_cooldown = 30
			ban_emote_timeout_msg = "banned emotes"
			ban_emote_timeout_duration = 1
			
			long_word_limit = 80
			
			ball_str = "!8ball"
			ball_list_str = "!8ball list"
			#move this up a level when we allow editing of these values
			#also maybe disable the list command? since they would likely be edting these values in a gui online.
			ball_arr = ["It is certain", "It is decidedly so", "Without a doubt", "Yes, definitely", "You may rely on it", "As I see it, yes", "Most likely", "Outlook good", "Yes", "Signs point to yes", "Reply hazy try again", "Ask again later", "Better not tell you now", "Cannot predict now", "Concentrate and ask again", "Don't count on it", "My reply is no", "My sources say no", "Outlook not so good", "Very doubtful"]
			
			ban_emote_str = "!ban emote"
			unban_emote_str = "!unban emote"
			
			chatters_str = "!chatters"
			viewers_str = "!viewers"
			subscribers_str = "!subscribers"
			subs_str = "!subs"	
				
				
			
			while stream_online(channel_parsed) == True:
				'''
				alright for some reason nothing in this entire while loop happens until a message is sent
				the same thing happens in tecsbot.py so this must be a core issue
				only when irc.send happens does anyof this ever get executed
				
				
				'''
				irc.setblocking(0)
				socket_ready = select.select([irc], [], [], 0)
				if socket_ready[0]:
					data = irc.recv(1204) #gets output from IRC server
					
					if data:
						if data.find("PING") != -1:
							str = "PONG :tmi.twitch.tv\r\n".encode
							irc.send("PONG :tmi.twitch.tv\r\n".encode("utf-8")) #responds to PINGS from the server
							print "Ponging..."
						data_arr = data.split(":", 2)
						if len(data_arr) == 3:
							user = (data_arr[1].split("!"))[0]
							msg = data_arr[2]
							msg = msg.rstrip()
							#for even printing
							if len(user) < 7:
								print "%s:\t\t\t%s" % (user, msg)
							elif len(user) < 16:
								print "%s:\t\t%s" % (user, msg)
							else:
								print "%s:\t%s" % (user, msg)
							'''
							#this is already in channel settings
							#offensive word timeouts
							for blacklist in blacklist_arr:
								if blacklist in msg:	
									#time out the user(ban from chat) for blacklist_timeout amount of seconds
									timeout(user, irc, timeout)
							'''
							#holy shit wish i thought of this earlier
							#only for debugging and development, will immediately stop execution of program
							if "exit" == msg:
								os._exit(1)
							#link whitelists
							#has to be before anti spam so that adding/removing a link will not trigger and time out the user doing so
							if link_whitelist_on:
								if in_front(link_whitelist_str, msg):
									if is_mod(user, channel_parsed):
										msg_arr = msg.split(" ")
										if in_front(link_whitelist_add_str, msg):
											if len(msg_arr) > 3:
												link_whitelist = msg_arr[3]
												link_whitelist_arr.append(link_whitelist)
												send_str = "%s%s added to list of whitelisted links.\r\n" % (pre_msg, link_whitelist)
											else:
												send_str = "%sUsage: \"!link whitelist add <link>\"\r\n" % pre_msg
										elif in_front(link_whitelist_del_str, msg) or in_front(link_whitelist_rem_str, msg):
											if len(msg_arr) > 3:
												link_whitelist = msg_arr[3]
												if is_num(link_whitelist):
													#we add on one to the actual index because users prefer to start with 1, rather than 0.
													link_whitelist = int(link_whitelist)
													if ((len(link_whitelist_arr)-1) >= link_whitelist-1):
														send_str = "%sLink %s removed at index %s.\r\n" % (pre_msg, link_whitelist_arr[link_whitelist-1], link_whitelist)
														del link_whitelist_arr[link_whitelist-1]
													else:
														send_str = "%sInvalid index for link removal.\r\n" % pre_msg
												else:
													if link_whitelist in link_whitelist_arr:
														link_whitelist_arr.remove(link_whitelist)
														send_str = "%sLink %s removed.\r\n" % (pre_msg, link_whitelist)									
													else:
														send_str = "%sSpecified link does not exist.\r\n" % pre_msg
											else:
												send_str = "%sUsage: \"!link whitelist delete/remove <link/index>\"\r\n" % pre_msg
										elif link_whitelist_list_str == msg:
												if len(link_whitelist_arr) == 0:
													send_str = "%sNo active links.\r\n" % pre_msg
												else:
													send_str = "%sActive links: " % pre_msg
													for link_whitelist in range(len(link_whitelist_arr)):
														if (link_whitelist != len(link_whitelist_arr) -1):
															#every element but last one
															send_str += "(%s.) %s, " % (link_whitelist+1, link_whitelist_arr[link_whitelist])
														else:
															#last element in arr
															send_str += "(%s.) %s.\r\n" % (link_whitelist+1, link_whitelist_arr[link_whitelist])
										elif link_whitelist_clr_str == msg:
											link_whitelist_arr = []
											send_str = "%sAll links removed.\r\n" % pre_msg
										elif link_whitelist_str == msg:
											send_str = "%sAdd or remove links to timeout users who say them. Syntax and more information can be found in the documentation.\r\n" % pre_msg
										irc.send(send_str)
									else:
										send_str = "%sYou have to be a mod to use !list whitelist commands.\r\n" % pre_msg
										irc.send(send_str)
							#spam permits
										if in_front(set_roulette_str, msg)
							if in_front(permit_str, msg):\
								if is_mod(user, channel_parsed):
									msg_arr = msg.split(" ")
									if len(msg_arr) == 2:
										permit_user = msg_arr[1]
										current_time = time.time()
										permit_pair = [current_time, permit_user]
										permit_arr.append(permit_pair)
										'''permit_dict[current_time] = []
										permit_dict[current_time].append(0)
										permit_dict[current_time][0] = permit_user'''
										#[[<current unix time> : <user who is permitted>],[],...]
										send_str = "%s%s's spam filter has been lifted for %s seconds\r\n" % (pre_msg, permit_user, permit_time)
									
										#possible future functionality
										'''#manual delete/remove
										elif permit_del_str in msg or permit_rem_str in msg:
											if len(msg_arr) == 3:
												permit_user = msg_arr[2]
												if is_num(permit_user):
													if ((len(permit_arr)-1) >= int(permit_user)-1):
														send_str = "%sPermit %s removed at index %s.\r\n" % (pre_msg, permit_arr[int(permit_user)][1], permit_user)
														#should be the same index as the pair, after all.
														del permit_arr[int(permit_user)]
													else:
														send_str = "%sInvalid index for permit removal.\r\n" % pre_msg										
												else:
													for permit_pair in permit_arr:
														if permit_user == permit_pair[1]:
															permit_arr.remove(permit_pair)
															send_str = "%sPermit \"%s\" removed.\r\n" % (pre_msg, permit_user)		
															break
													else:
														send_str = "%sSpecified permit does not exist.\r\n" % pre_msg
											else:
												#incorrectly formatted, display usage
												send_str = "%sUsage: \"!permit delete/remove <user/index>\".\r\n" % pre_msg
										#list
										elif permit_list_str == msg:
											if len(permit_arr) == 0:
												send_str = "%sNo users with active permits.\r\n" % pre_msg
											else:
												send_str = "%sUsers with active permits: " % pre_msg
												for permit_pair in range(len(permit_arr)):
													if (permit_pair != len(permit_arr) -1):
														#every element but last one
														send_str += "(%s.) %s, " % (permit_pair+1, permit_arr[permit_pair][1])
													else:
														#last element in arr
														send_str += "(%s.) %s.\r\n" % (permit_pair+1, permit_arr[permit_pair][1])
										#clear
										elif permit_clr_str == msg:
											permit_arr = []
											send_str = "%sAll permits removed.\r\n" % pre_msg'''
									#normal
									elif permit_str == msg:
										send_str = "%sUsage: \"!permit <user>\"\r\n" % pre_msg
									#idk
									else:
										send_str = "%sUsage: \"!permit <user>\"\r\n" % pre_msg
								else:
									send_str = "%sYou have to be a mod to permit users.\r\n" % pre_msg
								irc.send(send_str)	
							current_time = time.time()
							if in_front(unpermit_str, msg):
								if is_mod(user, channel_parsed):
									msg_arr = msg.split(" ")
									if len(msg_arr) == 2:
										permit_user = msg_arr[1]
										for permit_pair in permit_arr:
											if permit_pair[1] == permit_user:
												permit_arr.remove(permit_pair)
												break
									else:
										send_str = "%sUsage: \"!permit <user>\"\r\n" % pre_msg
								else:
									send_str = "%sYou have to be a mod to permit users.\r\n" % pre_msg
								irc.send(send_str)
							#remove from the permit_dict once they have been there more than the permit_time\
							#do we need to put this outside the loop?
							for permit_pair in permit_arr:
								user_time = permit_pair[0]
								if permit_pair[1] != nick:
									#don't remove tecsbot
									if ((current_time - user_time) >= permit_time):
										#changed this to remove because pop = unnecessary
										permit_arr.remove(permit_pair)
										#we could just break here but I would feel guilty, lets hope it works for now, if it doesnt we can either:
											#a) break here, making there a short delay in de-permitting people if there are a lot of them
											#b) figure out a way to reloop, or something so that it continues going through the dictionary even though elements in it have been removed.
									
							#antispam
							#add time, user, and message to array of 30second old messages
							'''perma permit for tecsbot avoids this
							if len(permit_arr) != 0:
								for permit_pair in permit_arr:
									if user not in '''
							if antispam_on:
								for permit_pair in permit_arr:
									if user not in permit_pair:
										if repeat_antispam_on == True:
											#general spam - need to improve this, for now adding in the set
											#needs to be in similar format to others for easy integration
											current_time = time.time() #unix time of message sent
											msg_data_arr = [current_time, user, msg]
											for msg_data in msg_info_arr:
												if msg_data_arr[0] - msg_data[0] < spam_cooldown: #only see messages that are within 30 seconds of newest messages
													if msg_data_arr[1] == msg_data[1] and msg_data_arr[2] == msg_data[2]: #if new message has the same user and same message as a previous message
														#if identical new message was sent within spam cooldown, then timeout user and stop looking through messages
														for permit_pair in permit_arr:
															if permit_pair[1] == user: 
																#if user is permitted to spam, don't time him out
																break
														else:
															timeout(user, irc, pre_msg, spam_timeout)
														break
												else:
													#pop the element out, since it no longer is within 30 seconds of the first message.
													msg_info_arr.remove(msg_data)
											msg_info_arr.insert(0, msg_data_arr)#add in the new message to the beginning of the list
										
										#emote spam
										if emote_antispam_on:
											msg_emote_count = 0
											for emote in emote_arr:
												if msg.count(emote) != 0:
													msg_emote_count += msg.count(emote)
												if msg_emote_count >= emote_max:
													emote_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, emote_warn_arr, emote_warn_duration, emote_warn_cooldown, emote_timeout_msg, emote_timeout_duration)
													break
										#caps spam
										if caps_antispam_on:
											if len(msg) >= caps_perc_min_msg_len:
												if caps_perc(msg) >= 60:
													caps_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, caps_warn_arr, caps_warn_duration, caps_warn_cooldown, caps_timeout_msg, caps_timeout_duration)
													break
										#fake purges
										if fake_purge_antispam_on:
											if msg in fake_purge_arr:
												fake_purge_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, fake_purge_warn_arr, fake_purge_warn_duration, fake_purge_warn_cooldown, fake_purge_timeout_msg, fake_purge_timeout_duration)
												break
										#!skincode
										if skincode_antispam_on:
											if is_front(skincode_msg, msg):
												skincode_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, skincode_warn_arr, skincode_warn_duration, skincode_warn_cooldown, skincode_timeout_msg, skincode_timeout_duration)
												break
										#long messages
										#lmao it was timing itself out need to have a permanent permit for tecsbot
										if long_msg_antispam_on:
											if len(msg) > msg_length_max:
												long_msg_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, long_msg_warn_arr, long_msg_warn_duration, long_msg_warn_cooldown, long_msg_timeout_msg, long_msg_timeout_duration)
												break
										#zalgo symbols
										#Very likely this will take a lot of time, find more efficient method if so
										if zalgo_antispam_on:
											for char in msg:
												if isinstance(char, unicode):
													print char
													if unicodedata.combining(char) != 0:
														sys.exit("zalgo detected")
														zalgo_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, zalgo_warn_arr, zalgo_warn_duration, zalgo_warn_cooldown, zalgo_timeout_msg, zalgo_timeout_duration)
														break
										#block symbols
										

										#dongers
										

										#excessive symbols
										#if there are more than min_symbol_chars in message, check the percentage and amount
										if symbol_antispam_on:
											if len(msg) > min_symbol_chars:
												symbol_num = symbol_count(msg)
												symbol_perc = float(symbol_num) / len(msg)
												#if the limits are exceeded for num or percentage
												if symbol_num > max_symbol_num or symbol_perc > max_symbol_perc:
													symbol_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, symbol_warn_arr, symbol_warn_duration, symbol_warn_cooldown, symbol_timeout_msg, symbol_timeout_duration)
													break
										#links
										#need a way to parse out the link exactly, instead of just checking if ours is in the link
										#we can split by spaces, look at each one and see if it contains any of these, thus making it a link and allowing us to parse and do tthe things
										#how to do the *path things? for now it's exact match
										if link_antispam_on:
											for word in msg.split(" "):
												if 'http://' in word or 'www.' in word or '.com' in word:#can we remove this and it be ok <-- we need to
													#word is a link
													for link_whitelist in link_whitelist_arr:
														if "*" in link_whitelist:
															link_whitelist_wcard = link_whitelist_wcard.split("*")
															#this way if there is any part that is not in the word, it will move on
															#however if they are all in the word, it will do the else statement
															for link_wcard_part in link_whitelist_wcard:
																if link_wcard_part not in word:#time them out and break
																	link_whitelist_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, link_whitelist_warn_arr, link_whitelist_warn_duration, link_whitelist_warn_cooldown, link_whitelist_timeout_msg, link_whitelist_timeout_duration)
																	break
															else:#the link was a pardoned one, let them free
																break
														else:
															if link_whitelist == word:
																break
													else:
														#link isn't whitelisted, time out user 
														link_whitelist_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, link_whitelist_warn_arr, link_whitelist_warn_duration, link_whitelist_warn_cooldown, link_whitelist_timeout_msg, link_whitelist_timeout_duration)
														break
														
										#these need to be different types
										msg_arr = msg.split(" ")
										#long word spam
										if long_word_antispam_on:
											for word in msg_arr:
												if len(word) > long_word_limit and '\n' not in word:
													long_word_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, long_word_warn_arr, long_word_warn_duration, long_word_warn_cooldown, long_word_timeout_msg, long_word_timeout_duration)
													break
										#/me
										if me_antispam_on:
											if is_front(me_msg, msg):
												me_warn_arr = warn(user, msg, pre_msg, channel_parsed, irc, me_warn_arr, me_warn_duration, me_warn_cooldown, me_timeout_msg, me_timeout_duration)
												break
										'''the complicated general antispam that moobot offers
										if len(msg) > min_spam_chars:
											#idk how to go about making this without killing speed of program		
											pass'''
										break
								else:
									pass
							#banphrase
							if banphrase_on:
								msg_arr = msg.split(" ")
								if in_front(banphrase_str, msg):
									if is_mod(user, channel_parsed): 
										if in_front(banphrase_add_str, msg):
											#if is_mod(user, channel_parsed):
											if len(msg_arr) > 2:#need to have this if statement more often
												banphrase = msg_arr[2]
												banphrase_arr.append(banphrase)
												send_str = "%s\"%s\" added to list of banphrases.\r\n" % (pre_msg, banphrase)
											else:
												send_str = "%sUsage: \"!banphrase add <banphrase>\"" % pre_msg
											#else:
												#send_str = "%sYou have to be a mod to add banphrases.\r\n" % pre_msg
											#irc.send(send_str)
									
										elif in_front(banphrase_del_str, msg) or in_front(banphrase_rem_str, msg):
											#if is_mod(user, channel_parsed):
											if len(msg_arr) > 2:
												banphrase = msg_arr[2]
												if is_num(banphrase):
													#we add on one to the actual index because users prefer to start with 1, rather than 0.
													banphrase = int(banphrase)
													if ((len(banphrase_arr)-1) >= banphrase-1):
														send_str = "%sBanphrase %s removed at index %s.\r\n" % (pre_msg, banphrase_arr[banphrase-1], banphrase)
														del banphrase_arr[banphrase-1]
													else:
														send_str = "%sInvalid index for banphrase removal.\r\n" % pre_msg
												else:
													if banphrase in banphrase_arr:
														banphrase_arr.remove(banphrase)
														send_str = "%sBanphrase \"%s\" removed.\r\n" % (pre_msg, banphrase)									
													else:
														send_str = "%sSpecified banphrase does not exist.\r\n" % pre_msg
											else:
												send_str = "%sUsage: \"!banphrase delete/remove <banphrase/index>\"\r\n" % pre_msg
											#else:
												#send_str = "%sYou have to be a mod to remove banphrases.\r\n" % pre_msg	
											#irc.send(send_str)
										elif banphrase_list_str == msg:
											if len(banphrase_arr) == 0:
												send_str = "%sNo active banphrases.\r\n" % pre_msg
											else:
												send_str = "%sActive banphrases: " % pre_msg
												for banphrase in range(len(banphrase_arr)):
													if (banphrase != len(banphrase_arr) -1):
														#every element but last one
														send_str += "(%s.) %s, " % (banphrase+1, banphrase_arr[banphrase])
													else:
														#last element in arr
														send_str += "(%s.) %s.\r\n" % (banphrase+1, banphrase_arr[banphrase])
										elif banphrase_clr_str == msg:
											banphrase_arr = []
											send_str = "%sAll banphrases removed.\r\n" % pre_msg
										elif banphrase_str == msg:
											send_str = "%sAdd or remove banphrases to timeout users who say them. Syntax and more information can be found in the documentation.\r\n" % pre_msg
										irc.send(send_str)
									else:
										send_str = "%sYou have to be a mod to use !banphrase commands.\r\n" % pre_msg
										irc.send(send_str)

							#test command if bot is in chat
							if msg == "!test":
								send_str = "%s%s\r\n" % (pre_msg, test_reply)
								irc.send(send_str)
							
							#autoreplies 
							if autoreply_on:
								if in_front(autoreply_str, msg):
									if is_mod(user, channel_parsed):
										#add autoreplies
										if in_front(autoreply_add_str, msg):
											msg_arr = msg.split(" ", 2)
											if len(msg_arr) == 3:
												if ":" in msg_arr[2]:
													ar_msg_arr = msg_arr[2].split(":")
													if len(ar_msg_arr) == 2:
														ar_phrase = ar_msg_arr[0]
														ar_reply = ar_msg_arr[1]
														ar_pair = [ar_phrase, ar_reply]
														ar_arr.append(ar_pair)
														#[phrase[reply],phrase[reply]]hopefully
														send_str = "%sPhrase \"%s\" added, with reply \"%s\".\r\n" % (pre_msg, ar_phrase, ar_reply)
													else:
														#incorrectly formatted, display usage
														send_str = "%sUsage: \"!autoreply add <phrase>:<reply>\".\r\n" % pre_msg
												else:
													#incorrectly formatted, display usage
													send_str = "%sUsage: \"!autoreply add <phrase>:<reply>\".\r\n" % pre_msg
											else:
												#incorrectly formatted, display usage
												send_str = "%sUsage: \"!autoreply add <phrase>:<reply>\".\r\n" % pre_msg
										#delete autoreplies
										elif in_front(autoreply_del_str, msg) or in_front(autoreply_rem_str, msg):
											msg_arr = msg.split(" ", 2)
											if len(msg_arr) == 3:
												ar_phrase = msg_arr[2]
												if is_num(ar_phrase):
													if ((len(ar_arr)-1) >= int(ar_phrase)-1):
														send_str = "%sAutoreply %s removed at index %s.\r\n" % (pre_msg, ar_arr[int(ar_phrase)], ar_phrase)
														#should be the same index as the pair, after all.
														del ar_arr[int(ar_phrase)]
													else:
														send_str = "%sInvalid index for autoreply removal.\r\n" % pre_msg										
												else:
													for ar_pair in ar_arr:
														if ar_phrase == ar_pair[0]:
															ar_arr.remove(ar_pair)
															send_str = "%sAutoreply \"%s\" removed.\r\n" % (pre_msg, ar_phrase)		
															break
													else:
														send_str = "%sSpecified autoreply does not exist.\r\n" % pre_msg
											else:
												#incorrectly formatted, display usage
												send_str = "%sUsage: \"!autoreply delete/remove <phrase/index>\".\r\n" % pre_msg
										#list autoreplies
										elif autoreply_list_str == msg:
											#check to make sure there are autoreplies to list
											if len(ar_arr) == 0:
												send_str = "%sNo active autoreplies.\r\n" % pre_msg
											else:
												send_str = "%sActive autoreplies: " % pre_msg
												for ar_pair in range(len(ar_arr)):
													ar_phrase = ar_arr[ar_pair][0]
													ar_reply = ar_arr[ar_pair][1]
													if (ar_pair != len(ar_arr)-1):
														#every element but last one
														send_str += "(%s.) %s: %s, " % (ar_pair+1, ar_phrase, ar_reply)
													else:
														#last element in arr
														send_str += "(%s.) %s: %s.\r\n" % (ar_pair+1, ar_phrase, ar_reply)
										
										#clear autoreplies
										elif autoreply_clr_str == msg:
											ar_arr = []
											send_str = "%sAll autoreplies removed.\r\n" % pre_msg
										#just autoreply string, display usage
										elif autoreply_str == msg:
											send_str = "%sAdd or remove phrases that trigger automatic replies. Syntax and more information can be found in the documentation.\r\n" % pre_msg
									else:
										send_str = "%sYou have to be a mod to use !autoreply commands.\r\n" % pre_msg
									irc.send(send_str)
							#sets			

							if is_front(set_str, msg):
								if is_mod(user, channel_parsed):
									msg_arr = msg.split(" ")
									if len(msg_arr) == 3:
										#turn roulette on or off
										if in_front(set_roulette_str, msg):
											rol_on = set_value(rol_on, "roulette", msg_arr, irc)
											
										#turn 8ball on or off
										if in_front(set_ball_str, msg):
											ball_on - set_value(ball_on, "8ball", msg_arr, irc)
											
										#banphrases
										if in_front(set_banphrase_str, msg):
											banphrase_on = set_value(banphrase_on, "banphrase", msg_arr, irc)
										
										#autoreplies
										if in_front(set_autoreply_str, msg):
											autoreply_on = set_value(autoreply_on, "autoreply", msg_arr, irc)
											
										#antispam
										if in_front(set_antispam_str, msg):
											antispam_on = set_value(antispam_on, "antispam", msg_arr, irc)
											
										#repeat
										if in_front(set_repeat_str, msg):
											repeat_on = set_value(repeat_on, "repeat", msg_arr, irc)
									
									elif len(msg_arr) == 4:
										#repeat antispam
										if in_front(set_repeat_antispam_str, msg):
											repeat_antispam_on = set_value(repeat_antispam_on, "repeat antispam", msg_arr, irc)
											
										#emote antispam
										if in_front(set_emote_antispam_str, msg):
											emote_antispam_on = set_value(emote_antispam_on, "emote antispam", msg_arr, irc)
											
										#caps antispam
										if in_front(set_caps_antispam_str, msg):
											caps_antispam_on = set_value(caps_antispam_on, "caps antispam", msg_arr, irc)
										
										#skincode antispam
										if in_front(set_skincode_antispam_str, msg):
											skincode_antispam_on = set_value(skincode_antispam_on, "skincode antispam", msg_arr, irc)
										
										#zalgo antispam
										if in_front(set_zalgo_antispam_str, msg):
											zalgo_antispam_on = set_value(zalgo_antispam_on, "zalgo antispam", msg_arr, irc)
										
										#symbol antispam
										if in_front(set_symbol_antispam_str, msg):
											symbol_antispam_on = set_value(symbol_antispam_on, "symbol antispam", msg_arr, irc)
										
										#link antispam
										if in_front(set_link_antispam_str, msg):
											link_antispam_on = set_value(link_antispam_on, "link antispam", msg_arr, irc)
										
										#me antispam
										if in_front(set_me_antispam_str, msg):
											me_antispam_on = set_value(me_antispam_on, "me antispam", msg_arr, irc)
											
										#ban emotes
										if in_front(set_ban_emotes_str, msg):
											ban_emotes_on = set_value(ban_emotes_on, "ban emotes", msg_arr, irc)
										
										#emote stats
										if in_front(set_emote_stats_str, msg):
											emote_stats_on = set_value(emote_stats_on, "emote stats", msg_arr, irc)
											
											
									elif len(msg_arr) == 5:
										#fake purge antispam
										if in_front(set_fake_purge_antispam_str, msg):
											fake_purge_antispam_on = set_value(fake_purge_antispam_on, "fake purge antispam", msg_arr, irc)
										
										#long message antispam
										if in_front(set_long_msg_antispam_str, msg):
											long_msg_antispam_on = set_value(long_msg_antispam_on, "long message antispam", msg_arr, irc)
										
										#long word antispam
										if in_front(set_long_word_antispam_str, msg):
											long_word_antispam_on = set_value(long_word_antispam_on, "long word antispam", msg_arr, irc)
									else:
										#usage
											send_str = "%sUsage: \"!set <feature> on/off \".\r\n" % pre_msg
									#just set_str, explain usage.
									if set_str == msg:
										send_str = "%sTurn features on or off. Usage: \"!set <feature> on/off \".\r\n" % pre_msg
									irc.send(send_str)
								else:
									#not mod
									send_str = "%sYou have to be a mod to use !set commands.\r\n" % pre_msg
									irc.send(send_str)
							#welcome newcomers - seems to be working with viewers and followers atm - need to figure out subs however
							#NOTE: TEMPORARILY DISABLED BECAUSE IT IS ANNOYING AS FUCK WHEN NOT PERMANENTLY ONLINE
							#new viewers
								#need to auth for sub list
							'''if user not in viewer_arr:
								#add to viewer_arr and then welcome them
								viewer_arr.append(user)
								send_str = "%sHello newcomer %s, welcome to %s's channel!\r\n" % (pre_msg, user, channel_parsed)
								irc.send(send_str)'''
							#new followers
							follower_arr = new_follower(follower_arr, channel_parsed, pre_msg)
							
							#uptime
							if uptime_str == msg:
								irc.send(get_uptime_str())
							
							#voting
							######################################################################################
							#non mods votes not being input
							#just needed %% to fix the problem, good luck future self I hope the SAT went well
							#-we'll see when we get the SAT scores wont we
							msg_arr = msg.split(" ", 2)
							if len(msg_arr) >= 2:
								if msg_arr[0] == vote_str:
									if msg_arr[1] == "start" and len(msg_arr) >= 3:
										#reset vote stuffs
										vote_dict = {}
										vote_users = []
										vote_on = True
										send_str = "%sPoll opened! To vote use " % pre_msg
										vote_option_arr = msg_arr[2].split(",")
										for vote_option in range(len(vote_option_arr)): 
											vote_dict[vote_option_arr[vote_option]] = [0]
											if vote_option != len(vote_option_arr) -1:
												send_str += "\"!vote %s\"/" % vote_option_arr[vote_option]
											else:
												send_str += "\"!vote %s\"\r\n" % vote_option_arr[vote_option]
										irc.send(send_str)		
									elif msg_arr[1] == "reset":
										vote_dict = {}
										send_str = "%sVotes reset.\r\n" % pre_msg
									elif msg_arr[1] == "results":
										if vote_on:
											if is_mod(user, channel_parsed):
												
												value_dict = sorted(vote_dict.items(), key=operator.itemgetter(1))
												if vote_total != 0:
													send_str = "%sCurrent Poll Results: " % pre_msg
													for pair in value_dict:
														key = pair[0]
														value = pair[1][0]
														send_str += "%s: %s%% " % (key, (float(value) / vote_total) * 100)
													send_str += "Total votes: %s\r\n" % vote_total
													#display current results
												else:
													#prevent divide by 0 error.
													send_str = "%sNo votes to display.\r\n" % pre_msg
											else:
												send_str = "%sYou have to be a moderator to display the current poll results.\r\n" %pre_msg
										else:
											send_str = "%sThere are no ongoing votes.\r\n" % pre_msg
										irc.send(send_str)
									elif msg_arr[1] == "end": #/close?
										#close the vote
										if is_mod(user, channel_parsed):
											vote_on = False
											send_str = "%sPoll Results: " % pre_msg
											value_dict = sorted(vote_dict.items(), key=operator.itemgetter(1))
											if vote_total != 0:
												for pair in value_dict:
													key = pair[0]
													value = pair[1][0]
													send_str += "%s: %s%% " % (key, (float(value) / vote_total) * 100)
												send_str += "Total votes: %s\r\n" % vote_total
											else:
												send_str = "%sNo votes to display.\r\n" % pre_msg
											irc.send(send_str)
									else:
										for vote_option in vote_option_arr:
											if msg_arr[1] == vote_option and user not in vote_users:
												#input vote if user hasnt already voted
												vote_dict[vote_option][0] += 1
												vote_users.append(user)
												vote_total+=1
							if msg == vote_str:
								send_str = "%To vote use " % pre_msg
								for vote_option in range(len(vote_option_arr)): 
									if vote_option != len(vote_option_arr) -1:
										send_str += "\"!vote %s\"/" % vote_option_arr[vote_option]
									else:
										send_str += "\"!vote %s\"\r\n" % vote_option_arr[vote_option]
								irc.send(send_str)		
									
							#raffle
							if start_raffle_str == msg:
								if is_mod(user, channel_parsed) == True:
									raffle_on = True
									send_str = "%sRaffle started. Join the raffle with \"!raffle\".\r\n" % (pre_msg)
								else:
									send_str = "%s%s only mods can start raffles.\r\n" % (pre_msg, user)
								irc.send(send_str)
								
							if raffle_on == True:
								#avoid duplicatess
								if join_raffle_str == msg and user not in raffle_users:
									raffle_users.append(user)
								if end_raffle_str == msg:
									if is_mod(user, channel_parsed) == True:
										winner = raffle_users[random.randint(0, (len(raffle_users) - 1))]
										#need to have prize of some sorts?
										send_str = "%s%s has won the raffle!\r\n" % (pre_msg, winner)
										irc.send(send_str)
										raffle_on = False
									else:
										send_str = "%s%s only mods can end raffles.\r\n" % (pre_msg, user)
										irc.send(send_str)
							#roulette
							#if user is mod then say it doesnt kill you or something
							if rol_on:
								if is_front(rol_cmd_str, msg):
									if rol_cmd_str == msg:
										#trigger roulette - allow custom messages for win/loss to replace default ones
										send_str = "%s/me places the revolver to %s's head\r\n" % (pre_msg, user)
										irc.send(send_str)
										#for dramatic effect
											#definitely allow editing of this time
										time.sleep(2)
										if random.random() < rol_chance:
											#time out the user(ban from chat) for rol_timeout amount of seconds
											if is_mod(user, channel_parsed) == False:
												timeout(user, irc, pre_msg, rol_timeout)
												send_str = "%sThe trigger is pulled, and the revolver fires! %s lies dead in chat\r\n" % (pre_msg, user)
											else:
												send_str = "%sThe gun jams thanks to your super mod powers. %s lives!\r\n" % (pre_msg, user)
											irc.send(send_str)
										else:
											#do nothing, notify of victory
											send_str = "%sThe trigger is pulled, and the revolver clicks. %s has lived to survive roulette!\r\n" % (pre_msg, user)
											irc.send(send_str)
									if is_front(rol_chance_str, msg):
										#get the new chance for ban in roulette
										msg_arr = msg.split(" ")
										#percentage is input as chance, *.01 to change to decimal
										input_perc = int(msg_arr[2])
										if input_perc > 100 or input_perc < 0:
											send_str = "%sPlease input a percentage chance for roulette to be triggered, i.e. \"!roulette chance 50\". Chance must be greater than zero, and less than 100.\r\n" % pre_msg
											irc.send(send_str)
											break
										else:
											rol_chance = input_perc * .01
											send_str = "%sRoulette chance successfully changed to %s%\r\n" % (pre_msg, input_perc)
											irc.send(send_str)
							
							#8ball
							if is_front(ball_list_str, msg):
								if is_mod(user, channel_parsed):
									send_str = "%sCurrent Possible 8ball responses: "
									for ball_response in range(len(ball_arr)):
										if (ball_response != len(ball_arr) -1):
											#if not last response in arr
											send_str += "(%s.)%s, " % (ball_response+1, ball_arr[ball_response])
										else:
											send_str += "(%s.)%s.\r\n" % (ball_response+1, ball_arr[ball_response])
								else:
									send_str = "%sOnly mods can list 8ball commands.\r\n" % pre_msg
								irc.send(send_str)
							if ball_on:
								if is_front(ball_str, msg): and "?" in msg:
									msg_arr = msg.split(" ", 1)
									if len(msg_arr) == 2:
										ball_response_index = random.randint(0, 19)
										ball_response = ball_arr[ball_response_index]
										send_str = "%sMagic 8 ball says...%s\r\n" % (pre_msg, ball_response)
									elif ball_str == msg:
										send_str = "%sGet the Magic 8 Ball to answer your question. Usage: \"!8ball <question> \".\r\n" % pre_msg
									else:
										send_str = "%sUsage: \"!8ball <question> \".\r\n" % pre_msg
									irc.send(send_str)
							
							#chatters
							if chatters_str == msg:
								chatter_data = get_json_chatters(channel_parsed)
								chatter_count = chatter_data["chatter_count"]
								send_str = "%sThere are currently %s accounts in chat.\r\n" % (pre_msg, chatter_count)
								irc.send(send_str)
								
							#viewers
							if viewers_str == msg:
								viewer_data = get_json_chatters(channel_parsed)
								viewer_arr = viewer_data["chatters"]["viewers"]
								viewer_count = len(viewer_arr) #i doubt this will work
								send_str = "%sThere are currently %s viewers in the channel.\r\n" % (pre_msg, viewer_count)
								irc.send(send_str)
							
							#subscribers
							if subs_str == msg or subscribers_str == msg:
								sub_data = get_json_subs(channel_parsed)
							
							#commercials
							if comm_str == msg:
								if is_streamer(user, channel_parsed):
									msg_arr = msg.split(" ")
									if len(msg_arr) == 1:
										#start default length commercial
										comm_len = 30
										start_commercial(comm_len, channel_parsed)
										send_str = "%s%s commercial started.\r\n" % (pre_msg, parse_sec(comm_len))
									elif len(msg_arr) == 2:
										comm_len = msg_arr[1]
										if is_num(comm_len):
											if comm_len in comm_len_arr:
												start_commercial(comm_len, channel_parsed)
												send_str = "%s%s commercial started.\r\n" % (pre_msg, parse_sec(comm_len))
										else:
											#display usage
											send_str = "%sUsage: !commercial <length of commercial>\r\n"
									else:
										#display usage
										send_str = "%sUsage: !commercial <length of commercial>\r\n"
								else:
									#not mod
									send_str = "%sYou have to be the current streamer in order to start commercials.\r\n" % pre_msg
								irc.send(send_str)
									
							#ban emotes
							if ban_emote_on:
								if is_front(ban_emote_str, msg):
									if is_mod(user, channel_parsed):
										msg_arr = msg.split(" ")
										if msg_arr == 3:
											ban_emote = msg_arr[2]
											ban_emote_arr.append(ban_emote)
											send_str = "%sEmote \"%s\" banned.\r\n" % (pre_msg, ban_emote)
										else:
											send_str = "%sUsage: \"!ban emote <emote>\"\r\n" % pre_msg
									else:
										send_str = "%sOnly mods can ban emotes.\r\n" % pre_msg
									irc.send(send_str)
									break
								if is_front(unban_emote_str, msg):
									if is_mod(user, channel_parsed):
										msg_arr = msg.split(" ")
										if msg_arr == 3:
											ban_emote = msg_arr[2]
											ban_emote_arr.remove(ban_emote)
											send_str = "%sEmote \"%s\" unbanned.\r\n" % (pre_msg, ban_emote)
										else:
											send_str = "%sUsage: \"!unban emote <emote>\"\r\n" % pre_msg
									else:
										send_str = "%sOnly mods can unban emotes.\r\n" % pre_msg
									irc.send(send_str)
									break
							
							#repeat commands
							#can easily be mod commands by just inputting /ban, /timeout, etc
							#need to put all commands in an array so that we can do !random command 
							#!repeat add <command> interval
							#concatenate all commands after [1] and before [len(arr)-1]
							
							if repeat_on:
								if is_front(repeat_str, msg):
									if is_mod(user, channel_parsed):
										if is_front(repeat_add_str, msg):
											msg_arr = msg.split(" ")
											if len(msg_arr) > 3:
												del msg_arr[0:2]#remove command specifiers
												repeat_cmd = ''
												for cmd_part in range(len(msg_arr)):
													if cmd_part == len(msg_arr)-1:
														repeat_cmd = repeat_cmd.rstrip()#get rid of trailing space
														repeat_interval = msg_arr[cmd_part]
													else:
														repeat_cmd += msg_arr[cmd_part] + " "
												current_time = time.time()
												repeat_set = [current_time, repeat_cmd, repeat_interval]
												repeat_arr.append(repeat_set)	
												send_str = "%sRepeat command \"%s\" added with interval %s.\r\n" % (pre_msg, repeat_cmd, parse_sec(repeat_interval))
											else:
												send_str = "%sUsage: !repeat add <command> <interval>\r\n" % pre_msg
										elif is_front(repeat_del_str, msg) or is_front(repeat_rem_str, msg):
											msg_arr = msg.split(" ", 2)
											if len(msg_arr) > 2:
												repeat_cmd = msg_arr[2]
												if is_num(repeat_cmd):
													if ((len(repeat_arr)-1) >= int(repeat_cmd)-1):
														send_str = "%sRepeat command \"%s\" with interval %s removed at index %s.\r\n" % (pre_msg, repeat_arr[int(repeat_cmd)-1][1], parse_sec(repeat_arr[int(repeat_cmd)-1][2]), repeat_cmd)
														#should be the same index as the pair, after all.
														del repeat_arr[int(repeat_cmd)-1]
													else:
														send_str = "%sInvalid index for repeat command removal.\r\n" % pre_msg										
												else:
													for repeat_set in repeat_arr:
														print repeat_set
														if repeat_cmd == repeat_set[1]:
															send_str = "%sRepeat command \"%s\" with interval %s removed.\r\n" % (pre_msg, repeat_cmd, parse_sec(repeat_set[2]))		
															repeat_arr.remove(repeat_set)
															break
													else:
														send_str = "%sSpecified repeat command does not exist.\r\n" % pre_msg	
											else:
												send_str = "%sUsage: !repeat delete/remove <command/index>\r\n" % pre_msg
										elif repeat_list_str == msg:
											if len(repeat_arr) == 0:
												send_str = "%sNo active repeat commands.\r\n" % pre_msg
											else:
												send_str = "%sActive repeat commands: " % pre_msg
												for repeat_set in range(len(repeat_arr)):
													repeat_cmd = repeat_arr[repeat_set][1]
													repeat_interval = repeat_arr[repeat_set][2]
													if (repeat_set != len(repeat_arr)-1):
														#every element but last one
														send_str += "(%s.) %s: %s, " % (repeat_set+1, repeat_cmd, parse_sec(repeat_interval))
													else:
														#last element in arr
														send_str += "(%s.) %s: %s.\r\n" % (repeat_set+1, repeat_cmd, parse_sec(repeat_interval))
										elif repeat_clr_str == msg:
											repeat_arr = []
											send_str = "%sAll repeat commands removed.\r\n" % pre_msg
										elif repeat_str == msg:
											send_str = "%sAdd or remove commands to be repeated every specified interval. Syntax and more information can be found in the documentation.\r\n" % pre_msg
										else:
											send_str = "%sUsage: !repeat <add/delete/remove/list/clear> <command> <interval>\r\n" % pre_msg
									else:
										#not moderino
										send_str = "%sYou have to be a mod to use !repeat commands.\r\n" % pre_msg
									irc.send(send_str)
									
									
							#########################3
							#this needs to be constantly checked, not just whenever a new message is sent. 
							#more threading will be necessary.
							'''#checking for repeats
							current_time = time.time()
							for repeat_set in repeat_arr:
								repeat_time = repeat_set[0]
								repeat_cmd = repeat_set[1]
								repeat_interval = repeat_set[2]
								print "%s,%s,%s,%s" % (current_time, repeat_time, repeat_cmd, repeat_interval) 
								if (current_time - repeat_time >= repeat_interval):
									repeat_set[0] = current_time#update the time
									send_str = "%s%s\r\n" % (pre_msg, repeat_cmd)
									irc.send(send_str)'''
									
							#custom commands - these are the exact same as autoreplies. Dont see how we need them.
							'''cmd_str = "!command"
							add_cmd_str = "!command add"
							del_cmd_str = "!command delete"
							rem_cmd_str = "!command remove"
							#do we need to add confirm dialogues here?
							if add_cmd_str in msg:
								msg_arr = msg.split(" ", 2)
								
								cmd = msg_arr[1]
								response = msg_arr[2] 
								
								#send_str = "%sAre you sure you want to add '%s' with response '%s'?\r\n" % (pre_msg, cmd, response)
								#irc.send(send_str)
								cmd_dict[cmd] = []
								cmd_dict[cmd].append(0)
								cmd_dict[cmd][0] = response
								
								send_str = "%sCommand \"%s\" successfully added, with response \"%s\".\r\n" % (pre_msg, cmd, response)
								irc.send(send_str)
								
							if del_cmd_str in msg:
								msg_arr = msg.split(" ", 1)
								cmd = msg_arr[1]
								if cmd in cmd_dict:
									#send_str = "%sAre you sure you want to remove '%s' with response '%s'?" % (pre_msg, cmd, cmd_dict[cmd][0])	
									#irc.send(send_str)
									#changed this to remove because pop = uncessary
									cmd_dict.remove(cmd)
									send_str = "%sCommand '%s' successfully removed.\r\n" % (pre_msg, cmd)
									irc.send(send_str)
								else:
									send_str = "%sCommand '%s' not found. Perhaps you misspelled it?\r\n" % (pre_msg, cmd)
									irc.send(send_str)
								
							
							for cmd in cmd_dict:
								if cmd == msg:
									send_str = "%s%s\r\n" % (pre_msg, cmd_dict[cmd][0])
									irc.send(send_str)'''
							if ban_emote_on:
								for ban_emote in ban_emote_arr:
									if ban_emote in msg:
										ban_emote_warn_arr = warn(user, msg, pre_msg, irc, ban_emote_warn_arr, ban_emote_warn_duration, ban_emote_warn_cooldown, ban_emote_timeout_msg, ban_emote_timeout_duration)
							if banphrase_on:
								for banphrase in banphrase_arr:
									if banphrase in msg:
										timeout(user, irc, pre_msg, banphrase_timeout)
										break
							if autoreply_on:
								for ar_pair in ar_arr:
									if ar_pair[0] == msg:
										send_str = "%s%s\r\n" % (pre_msg, ar_pair[1])
										irc.send(send_str)
										break
							#this is probably what's taking so long, changing this to be a one time addon to an array with a function 
							#emote related commands - need to handle custom emotes
							if emote_stats_on:
								for emote in emote_arr:
									if msg.count(emote) != 0:
										#update dictionary with emote
										emote_count = msg.count(emote)
										count_dict[emote][0] += emote_count
										stats_str = "!stats %s" % emote
										if stats_str == msg:
											emote_per_min = find_per_min(emote)
											send_str = "%sTotal times %s has been sent: %s. %s per minute: %s.\r\n" % (pre_msg, emote, count_dict[emote][0], emote, emote_per_min)
											irc.send(send_str)			
									
					else:
						print "Reconnecting..."
						irc.close()
						time.sleep(3)
						connect_channel(channel)
				else:#if there is no data on the socket(irc)
					#checking for repeats
					current_time = time.time()
					for repeat_set in repeat_arr:
						repeat_time = repeat_set[0]
						repeat_cmd = repeat_set[1] 
						repeat_interval = float(repeat_set[2]) 
						repeat_variance = .15
						repeat_interval = repeat_interval - repeat_variance
						#this will help for the small numbers in making that gap less forward, if possible.
						#using a percentage would quickly cause large inaccuracies in larger intervals, and only using a percentage for small ones would be so small that it did not matter. There is no perfect solution to this.
						#this way at least numbers that would result in being more late, i.e. .95 -> 1.3 are shortened considerably, while not affecting larger numbers
						#################
						print current_time - repeat_time
						if (current_time - repeat_time >= repeat_interval):
							repeat_set[0] = current_time#update the time
							send_str = "%s%s\r\n" % (pre_msg, repeat_cmd)
							#debugging stuff
							#send_str = "%s%s : %s\r\n" % (pre_msg, current_time - repeat_time, repeat_interval)
							irc.send(send_str)
							

#main whisper bot where other threads with processes will be started
#sets variables for connection to twitch chat



#start channel bot thread
whisper_msg = ""
whisper_user = ""

try:
	thread.start_new_thread(channel_bot_start, ("#darkelement75",))
except Exception as errtxt:
	print errtxt
	
while True:
	data = irc.recv(1204) #gets output from IRC server
	if data != [] and data != '':
		if data.find("PING") != -1:
			str = "PONG :tmi.twitch.tv\r\n".encode
			irc.send("PONG :tmi.twitch.tv\r\n".encode("utf-8")) #responds to PINGS from the server
			#print "Ponging..."
		data_arr = data.split(":", 2)
		if len(data_arr) == 3:
			user = (data_arr[1].split("!"))[0]
			msg = data_arr[2]
			msg = msg.rstrip()
			#for even printing
			if len(user) < 7:
				print "%s:\t\t\t%s" % (user, msg)
			elif len(user) < 16:
				print "%s:\t\t%s" % (user, msg)
			else:
				print "%s:\t%s" % (user, msg)
				
				
		#when any of the threads change both values whisper the message and reset the values
		if whisper_msg != "" and whisper_user != "":
			whisper(whisper_user, whisper_msg, pre_msg_group)
			whisper_msg = ""
			whisper_user = ""
				
				
	else:
		irc.close()
		time.sleep(3)
		connect_group()
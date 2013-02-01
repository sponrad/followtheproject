def search_function:
    # you might want to store all search queries in your datastore, to use for improving content, etc.. -
    new_search = Search ()
    new_search.query = term
    new_search.put()

import re
# split the term into seperate words.
terms = term.split()
# get all the posts to search from in the database, we can't use LIKE, so this will have to suffice.
query = db.GqlQuery ("SELECT * FROM Post")
results = query.fetch(10)
# define found, this is the final results string, and partial - for partial matches.
found = "<h3>Exact Matches</h3><br />"
partial = "<h3>Partial Matches</h3><br />"
# go through all posts.
for result in results:
    # split posts into words, as well as periods, commas and dashes (so that "word." is split into ["word", "."]).
    words = re.split(r'[ .,-]', result.content)
# set count to 0 (count is used to keep track of the current index in the words list).
count = 0
# once the function has found a match in this result, we must break the loop.
do_query = True
for x in range(len(words)):
    # create a string that holds a sequence of words the lenth of the search query for exact matches.
    sear = words[x: x + len(terms)]
# temp is used to compile this sequence into a string, for it to be comparable with the query.
temp = ""
# compile temp -
for p in sear:
    temp += p + " "
# check to see if the compiled temp is equal to the query -
if do_query:
    if temp.lower() == (term.lower() + " "):
        # format the result in to a string, with 10 extra words (as description of the post) on either side of the result; make query term bold.
        formatted = ""
#  if the query has been found in this post -
do_query = False
for i in range(20):
    if i < 10:
        # words before the matched term; try statement in case there are less than 10 words before (hacky, but acceptable)
        try:
            formatted += words[count - (10-i)] + " "
        except:
            pass
    elif i > 10:
        try:
            formatted += words[count + (i-10)] + " "
        except:
            pass
if i == 10:
    # make the matched query bold for the results page -
    formatted += "<b> " + words[count] + " "
if i == (9 + len(terms)):
    formatted += "</b>"
# add the results to a formatted string of exact matches -
found += ("<a href='?p="+result.title+"'>"+result.title + "</a>" + "<p>..." +formatted + "...</p>")
count += 1
# now let's do some partial matches (will match any words, in any sequence). Adds only title to the formatted string.
do_query = True
for x in terms:
    for y in words:
        if x == y:
            if do_query:
                do_query = False
partial += "<a href='?p="+result.title+"'>"+result.title + "</a><br />"
# a formatted string to output to HTML including all matches, exact and partial -
res = ""
# check if there are any matches, if none return a friendly message -
if partial == "<h3>Partial Matches</h3><br />":
    return "No matches were found for your search query."
else:
    if found != "<h3>Exact Matches</h3><br />":
        res += found
res += partial
#return the results! -
return res

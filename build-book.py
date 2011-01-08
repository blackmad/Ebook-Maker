#!/usr/bin/python

# TODO
# cover image
# start page?
# magazine format?
#
# worst page ever:
#    Washington's I.T. Guy | The American Prospect
#                <!******************** -->

kindlegen = 'kindlegen'
ebook_convert = 'ebook-convert'

from time import strftime
import commands
import feedparser
import os
import sys
import urllib2
import ez_epub
import re
import csv
import unicodedata
import optparse
from BeautifulSoup import BeautifulSoup, Comment
from optparse import OptionParser
import xml.parsers.expat

def everything_between(content,begin,end):
  idx1=content.find(begin)
  idx2=content.find(end,idx1)
  return content[idx1+len(begin):idx2].strip()


def unescape(s):
    want_unicode = False
    if isinstance(s, unicode):
        s = s.encode('utf-8')
        want_unicode = True

    # the rest of this assumes that `s` is UTF-8
    list = []

    # create and initialize a parser object
    p = xml.parsers.expat.ParserCreate('utf-8')
    p.buffer_text = True
    p.returns_unicode = want_unicode
    p.CharacterDataHandler = list.append

    # parse the data wrapped in a dummy element
    # (needed so the 'document' is well-formed)
    p.Parse('<e>', 0)
    p.Parse(s, 0)
    p.Parse('</e>', 1)

    # join the extracted strings and return
    es = ''
    if want_unicode:
        es = u''
    return es.join(list)

files = []
count = 1

def get_title(url):
    data = urllib2.urlopen(url).read()
    title = everything_between(data,'<title>','</title>')
    return unescape(title)

def get_data(url):
    if use_boilerpipe:
      url = 'http://boilerpipe-web.appspot.com/extract?url=' + url
    print url
    data = urllib2.urlopen(url).read()
    return data

import urlparse
import os.path

def entry_date(e):
  try:
    return e.published_parsed
  except:
    try:
      return e.updated_parsed
    except:
      return e.created_parsed

def entry_date_str(e):
  return strftime('%a, %d %b %Y %H:%M:%S', entry_date(e))

def entry_get(x, key):
  if x.has_key(key):
    return x.get(key)
  return ''

def get_all_entries(url, entries):
  global book_title
  global author

  d = feedparser.parse(url)

  if d.feed.has_key('title') and not book_title:
    book_title = d.feed.title
  title = d.feed.title + '<br>' + d.feed.subtitle

  if not author:
    author = entry_get(d.feed, 'author')

  entries += d['entries']
  print 'entries size: %d' % len(entries)
  next_links = filter(lambda l: l.rel == 'next',  d.feed.links)
  if len(next_links):
    print 'getting next links'
    get_all_entries(next_links[0].href, entries)


def process_feed(file):
  entries = []
  get_all_entries(file, entries)

  for entry in reversed(entries):
    print 'adding: %s' % entry.title
    if full_content:
      content = entry_get(entry, 'content')
      if not content:
        content = entry_get(entry, 'summary')
      add_article(entry_get(entry, 'title'),
        '<html><body><h1>%s</h1><h3>%s</h3>%s</body></html>' % (
        entry_get(entry, 'title'),
        entry_date_str(entry),
        content))
    else:
      print entry.link
      data = get_data(entry.link)
      add_article(entry_get(entry, 'title'), data)

def process(row):
    url = row[0]
    title = None
    if len(row) == 2:
      if 'http' in row[0]:
        url, title = row
      if 'http' in row[1]:
        title, url = row

    if not title:
      title = get_title(url)
    data = get_data(url)
    add_article(title, data)

def add_article(title, data):
    global count
    # fix_images
    soup = BeautifulSoup(data)
    comments = soup.findAll(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]
    [script.extract() for script in soup.findAll('script')]
    [script.extract() for script in soup.findAll('noscript')]
    for a in soup.findAll('a'):
      for attr in a.attrs:
        if ':' in attr[1]:
          del a[attr[0]]

    for img in soup.findAll('img'):
      try:
        print 'img src: ' + img['src']
        img_url = img['src']
        if 'http' not in img_url:
          img_url = urlparse.urljoin(url, img_url)
        img_data = urllib2.urlopen(img_url).read()
        path = urlparse.urlsplit(img['src']).path
        print 'img path: ' + path
        img_filename = os.path.split(path)[1]
        output_path = os.path.join(output_tmp, img_filename)
        open(output_path, 'w').write(img_data)
        img['src'] = img_filename
        book.impl.addImage(output_path, img_filename)
      except:
        pass

    print 'title: ' + title
    section = ez_epub.Section()
    section.title = '%d: %s' % (count, title.decode('utf-8').encode('ascii', 'ignore'))
    count += 1
    #section.title = unicodedata.normalize('NFKD', title.encode('utf-8')).encode('ascii','ignore')
    section.html = True
    section.text = soup.prettify()
    sections.append(section)

usage = """
  usage %prog [options] input_file

  input file can be one of the following
  - a text file containing URLs to parse
  - a CSV file of the form title,url or url, title
  - a downloaded rss or atom file
  - a URL of an rss or atom feed """  
parser = OptionParser(usage=usage)

parser.add_option('-f', '--full', action='store_true', dest='full_content', default=False,
  help='Use content from RSS/Atom feed, rather than fetching links')
parser.add_option('-s', '--strip', action='store_true', dest='use_boilerpipe', default=True,
  help='Attempt to strip boilerplate from web content using https://boilerpipe-web.appspot.com/')
parser.add_option('-t', '--title', dest='title',
  help='Book Title')
parser.add_option('-a', '--author', dest='author',
  help='Book Author')
parser.add_option('-o', '--output', dest='output',
  help='Base name of output file & directory')
parser.add_option('-e', '--epub', action='store_true', dest='generate_epub', default=True,
  help='Generate an epub file')
parser.add_option('-k', '--kindle', action='store_true', dest='use_kindlegen', default=True,
  help='Generate a mobi (kindle) file using kindlegen')
parser.add_option('-c', '--calibre', action='store_true', dest='use_calibre', default=False,
  help='Generate a mobi (kindle) file using ebook-convert from calibre')

(options, args) = parser.parse_args()

if len(args) < 1:
  print 'Must specify an input source'
  parser.print_help()
  sys.exit(1)

file = args[0]

if not options.output:
  output = os.path.splitext(os.path.split(file)[1])[0]

author = options.author
book_title = options.title
use_boilerpipe = options.use_boilerpipe
print 'Using boilerpipe? ', 'Yes' if use_boilerpipe else 'No'
full_content = options.full_content
print 'Full content feed? ', 'Yes' if full_content else 'No'

output_tmp = '/tmp/' + os.path.basename(output) + '_tmp'
try:
  os.mkdir(output_tmp)
except:
  pass

book = ez_epub.Book()
sections = []
if not options.output and book_title:
  output = book_title
print "Processing: " + file
print 'Output: %s' % output
if 'rss' in file or 'http' in file or 'atom' in file or 'xml' in file:
  print "Processing as feed"
  process_feed(file)
else:
  print "Processing as csv/text input"
  f = open(file)
  csv_reader = csv.reader(f)
  for row in csv_reader:
    process(row)

if not options.output:
  output = book_title

print 'Title: %s' % book_title
print 'Author: %s' % author
book.title = book_title
book.authors = [author]
book.sections = sections
generate_epub = options.generate_epub or options.use_calibre
print 'Generating epub? ', 'Yes' if generate_epub else 'No'
book.make(output, generate_epub)

if options.use_kindlegen:
  kindle_cmd = '%s "%s/OEBPS/content.opf" -o "%s.mobi"' % (kindlegen, output, output)
  print(kindle_cmd)
  os.system(kindle_cmd)
  mv_cmd = 'mv "%s/OEBPS/%s.mobi" "%s.mobi"' % (output, output, output)
  print (mv_cmd)
  os.system(mv_cmd)

if options.use_calibre:
  calibre_cmd = '%s "%s.epub" -o "%s.mobi"' % (ebook_convert, output, output)
  print(calibre_cmd)
  os.system(calibre_cmd)

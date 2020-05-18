from bs4 import BeautifulSoup
import csv
import os.path
import re
import io
import argparse
from urllib.request import urlopen, Request

# urlopen(Request(url, headers={'User-Agent': 'Mozilla'}))


def parse_xml(rss_link):
    parse_xml_url = urlopen(Request(rss_link, headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.47 Safari/537.36'}))
    xml_page = urlopen(link).read()
    parse_xml_url.close()
    doc = BeautifulSoup(xml_page, 'xml')
    rss_item = doc.findAll("entry")
    rss_item.extend(doc.findAll("item"))
    return rss_item


def parse_and_write(rss_item):
    # parses xml and turns it into a list of dicts using bs4
    # rss list will contain dictionaries of all the items read from the rss feed
    global rss_content
    rss_content = []
    for item in rss_item:
        temp_dict = {}
        for child in [child for child in item.children if (child != "\n")]:
            temp_dict[str(child.name)] = child.text
        rss_content.append(temp_dict)
        del temp_dict

    if args.output:
        org_write_file_name = str(args.output)
    else:
        org_write_file_name = re.sub('(https|http)|[^\\w]', '', link) + ".csv"
    write_file_name, open_mode = check_write_file(org_write_file_name, org_write_file_name, 1)

    # if there's anything new to write, write dict into the new csv
    if len(rss_content) != 0:
        with open(write_file_name, open_mode) as write_file:
            csvwriter = csv.DictWriter(write_file, fieldnames=list(rss_content[0].keys()))
            # if new file write headers. If appending then don't.
            if open_mode == "w":
                csvwriter.writeheader()
            for entry in rss_content:
                csvwriter.writerow(entry)
    else:
        print("Nothing new to write from " + link)


# this function is called from parse_and_write
# this function sets the file name to write to.
# Also, if the write file exists it compares the write file and the rss input to avoid writing duplicate rows
def check_write_file(org_write_file_name, tentative_write_file_name, x):
    if os.path.isfile(tentative_write_file_name):
        open_mode = "a"
        # reads existing csv
        with open(tentative_write_file_name, "r") as csv_file:
            # compare the file's headers and the headers of the content being written and verify they're the same
            csv_reader = csv.reader(csv_file)
            for row in csv_reader:
                file_header = row
                break
            if file_header != list(rss_content[0].keys()):
                # headers are not the same
                # adds a _num to the file name before the file extension e.g. filename_2.csv
                tentative_write_file_name = org_write_file_name[
                                            :org_write_file_name[::-1].index('.') * -1 - 1] + "_" + str(
                    x) + org_write_file_name[org_write_file_name[::-1].index('.') * -1 - 1:]
                return check_write_file(org_write_file_name, tentative_write_file_name, x + 1)
            else:
                # headers are the same
                if not args.append:
                    if args.readall:
                        csv_file_lines = [x for x in csv.DictReader(csv_file, fieldnames=file_header)]
                        for row in csv_file_lines:
                            row_found = check_for_row(row, file_header)
                            if row_found:
                                rss_content.remove(row_found)
                    else:
                        # reads the last len(rss_content) + 100 lines of the csv file. +100 to make sure it got everything
                        csv_file_lines = tail(tentative_write_file_name, num_rss_items + 100)
                        for row in csv_file_lines:
                            row_found = check_for_row(row, file_header)
                            if row_found:
                                rss_content.remove(row_found)
                if len(rss_content) != 0:
                    print("Appending " + str(len(rss_content)) + " new lines to file " + tentative_write_file_name)
    else:
        open_mode = "w"
        print("Writing " + link + " to new file " + tentative_write_file_name)
    return tentative_write_file_name, open_mode


# this function can be called from check_write_file
def check_for_row(search_row, file_header):
    # return False if row is not found
    row_found = False
    if args.compare:
        if args.compare in file_header:
            search_row = dict(search_row)
            for new_row in rss_content:
                if search_row[args.compare] == new_row[args.compare]:
                    row_found=new_row
        else:
            raise SystemExit("Bad --compare value. There's no column for " + args.compare)
    else:
        if search_row in rss_content:
            row_found = search_row
    return row_found


# this function can be called from check_write_file
def tail(file_name, csv_lines):
    with open(file_name, 'rb') as f:
        """
        Returns the last `window` lines of file `f` as a list.
        f - a byte file-like object
        """
        # my trash
        with open(file_name, 'r') as csvfile:
            csv_reader = csv.reader(csvfile)
            for row in csv_reader:
                file_header = row
                break

        # will read max of 20000 lines
        window = 20000
        # end my trash

        if window == 0:
            return []
        BUFSIZ = 1024
        f.seek(0, 2)
        bytes = f.tell()
        size = window + 1
        block = -1
        data = []
        while size > 0 and bytes > 0:
            if bytes - BUFSIZ > 0:
                # Seek back one whole BUFSIZ
                f.seek(block * BUFSIZ, 2)
                # read BUFFER
                data.insert(0, f.read(BUFSIZ).decode('utf-8', 'ignore'))
            else:
                # file too small, start from begining
                f.seek(0, 0)
                # only read what was not read
                data.insert(0, f.read(bytes).decode('utf-8', 'ignore'))
                data = ''.join(data)

            # my trash
            output = io.StringIO(initial_value=''.join(data))
            regexp = "\n" + ",".join(['("(.|\n)*?(?<!")"(?!")|[^\n,"]*)' for _ in range(len(file_header))])
            # print(regexp)
            if len([x for x in re.findall(regexp, output.read(), re.MULTILINE)]) > csv_lines:
                output.seek(0)
                csv_reader = csv.DictReader(output, fieldnames=file_header)
                if len([x for x in csv_reader]) > csv_lines:
                    output.seek(0)
                    output_txt = output.getvalue()
                    # print(''.join(data)[output_txt.index(re.search(regexp, output_txt, re.MULTILINE).group()):])
                    data = ''.join(data)[output_txt.index(re.search(regexp, output_txt, re.MULTILINE).group()):]
                    del output_txt
                    break
            # end of my trash

            linesFound = data[0].count('\n')
            size -= linesFound
            bytes -= BUFSIZ
            block -= 1
        output = io.StringIO(initial_value=data)
        csv_reader = csv.DictReader(output, fieldnames=file_header)
        return [x for x in csv_reader]


# sets up command line arguments
parser = argparse.ArgumentParser(description='Reads rss feed(s) into a csv file')
parser.add_argument('urls', nargs="+", type=str, help='input rss feed link(s) here')
parser.add_argument('-o', '--output',
                    help="Specifies the output file. This option can be used with multiple inputs and if the rss headers are the same they will be written to the same file.")
parser.add_argument('--read-all', dest="readall", action='store_true',
                    help="Reads the whole csv file before writing to it instead of just the end.")
parser.add_argument('--compare', type=str,
                    help="Doesn't write new entries if the specified field matches existing entries. Generally causes fewer rows to be written. Example --compare guid")
parser.add_argument('--append', action='store_true', help="Appends all rss items to the csv without reading the existing file, if there is one")
args = parser.parse_args()

# gets all the rss content
rss_items = {}
for link in args.urls:
    rss_items[link] = parse_xml(link)

# gets the total number of rss items that were retrieved from the links
num_rss_items = sum([len(rss_items[link][:]) for link in rss_items][:])

# print(rss_items)
# parses and writes the rss content
for link in rss_items:
    parse_and_write(rss_items[link])

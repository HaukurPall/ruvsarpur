import argparse

from .ruvsarpur import *


def parseArguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-o", "--output", help="The path to the folder where the downloaded files should be stored", type=str
    )
    parser.add_argument("--sid", help="The series ids for the tv series that should be downloaded", type=str, nargs="+")
    parser.add_argument(
        "--pid", help="The program ids for the program entries that should be downloaded", type=str, nargs="+"
    )

    parser.add_argument(
        "-q",
        "--quality",
        help="The desired quality of the downloaded episode, default is 'Normal' which is Standard-Definition",
        choices=list(QUALITY_BITRATE.keys()),
        default="HD1080",
        type=str,
    )

    parser.add_argument("-f", "--find", help="Searches the TV schedule for a program matching the text given", type=str)

    parser.add_argument("--refresh", help="Refreshes the TV schedule data", action="store_true")

    parser.add_argument("--force", help="Forces the program to re-download shows", action="store_true")

    parser.add_argument("--list", help="Only lists the items found but nothing is downloaded", action="store_true")

    parser.add_argument("--desc", help="Displays show description text when available", action="store_true")

    parser.add_argument(
        "--keeppartial",
        help="Keep partially downloaded files if the download is interrupted (default is to delete partial files)",
        action="store_true",
    )

    parser.add_argument(
        "--checklocal",
        help="Checks to see if a local file with the same name already exists. If it exists then it is not re-downloaded but it's pid is stored in the recorded log (useful if moving between machines or if recording history is lost)'",
        action="store_true",
    )

    parser.add_argument(
        "-d", "--debug", help="Prints out extra debugging information while script is running", action="store_true"
    )

    parser.add_argument(
        "-p",
        "--portable",
        help="Saves the tv schedule and the download log in the current directory instead of {0}".format(LOG_DIR),
        action="store_true",
    )

    parser.add_argument(
        "--new",
        help="Filters the list of results to only show recently added shows (shows that have just had their first episode aired)",
        action="store_true",
    )

    parser.add_argument(
        "--originaltitle",
        help="Includes the original title of the show in the filename if it was found (this is usually the foreign title of the series or movie)",
        action="store_true",
    )

    parser.add_argument("--ffmpeg", help="Full path to the ffmpeg executable file", type=str)

    return parser.parse_args()


# The main entry point for the script
def main():
    try:
        init()  # Initialize the colorama library

        today = datetime.date.today()

        # Get the current working directory (place that the script is executing from)
        working_dir = sys.path[0]

        # Construct the argument parser for the commandline
        args = parseArguments()

        # Get ffmpeg exec
        ffmpegexec = findffmpeg(args.ffmpeg, working_dir)

        # Create the full filenames for the config files
        previously_recorded_file_name = createFullConfigFileName(args.portable, PREV_LOG_FILE)
        tv_schedule_file_name = createFullConfigFileName(args.portable, TV_SCHEDULE_LOG_FILE)

        # Get information about already downloaded episodes
        previously_recorded = getPreviouslyRecordedShows(previously_recorded_file_name)

        # Get an existing tv schedule if possible
        if not args.refresh:
            schedule = getExistingTvSchedule(tv_schedule_file_name)

        if args.refresh or schedule is None or schedule["date"].date() < today:
            schedule = {}

            # Downloading the full VOD available schedule as well
            for typeValue, catName in vod_types_and_categories:
                try:
                    schedule.update(getVodSchedule(typeValue, catName))
                except Exception as ex:
                    print(
                        "Unable to retrieve schedule for VOD category '{0}', no episodes will be available for download from this category.".format(
                            catName
                        )
                    )
                    continue

        # Save the tv schedule as the most current one, save it to ensure we format the today date
        saveCurrentTvSchedule(schedule, tv_schedule_file_name)

        if args.debug:
            for key, schedule_item in schedule.items():
                printTvShowDetails(args, schedule_item)

        # Now determine what to download
        download_list = []

        for key, schedule_item in schedule.items():

            # Skip any items that aren't show items
            if key == "date" or not "pid" in schedule_item:
                continue

            candidate_to_add = None
            # if the series id is set then find all shows belonging to that series
            if args.sid is not None:
                if "sid" in schedule_item and schedule_item["sid"] in args.sid:
                    candidate_to_add = schedule_item
            elif args.pid is not None:
                if "pid" in schedule_item and schedule_item["pid"] in args.pid:
                    candidate_to_add = schedule_item
            elif args.find is not None:
                if (
                    "title" in schedule_item
                    and fuzz.partial_ratio(args.find, createShowTitle(schedule_item, args.originaltitle)) > 85
                ):
                    candidate_to_add = schedule_item
                elif "title" in schedule_item and fuzz.partial_ratio(args.find, schedule_item["title"]) > 85:
                    candidate_to_add = schedule_item
                elif (
                    "original-title" in schedule_item
                    and not schedule_item["original-title"] is None
                    and fuzz.partial_ratio(args.find, schedule_item["original-title"]) > 85
                ):
                    candidate_to_add = schedule_item
            else:
                # By default if there is no filtering then we simply list everything in the schedule
                candidate_to_add = schedule_item

            # If the only new episode filter is set then only include shows that have recently started airing
            if args.new:
                # If the show is not a repeat show or hasn't got more than a single episode in total then it isn't considered a show so exclude it
                if (
                    not "ep_num" in schedule_item
                    or not "ep_total" in schedule_item
                    or int(schedule_item["ep_total"]) < 2
                    or int(schedule_item["ep_num"]) > 1
                ):
                    candidate_to_add = None  # If the show is beyond ep 1 then it cannot be considered a new show so i'm not going to add it

            # Now process the adding of the show if all the filter criteria were satisified
            if candidate_to_add is not None:
                download_list.append(candidate_to_add)

        total_items = len(download_list)
        if total_items <= 0:
            print("Nothing found to download")
            sys.exit(0)

        print(
            "Found {0} show(s)".format(
                total_items,
            )
        )

        # Sort the download list by show name and then by showtime
        download_list = sorted(download_list, key=itemgetter("pid", "title"))
        download_list = sorted(download_list, key=itemgetter("showtime"), reverse=True)

        # Now a special case for the list operation
        # Simply show a list of all the episodes found and then terminate
        if args.list:
            for item in download_list:
                printTvShowDetails(args, item)
            sys.exit(0)

        curr_item = 1
        for item in download_list:
            # Get a valid name for the save file
            local_filename = createLocalFileName(item, args.originaltitle)

            # Create the display title for the current episode (used in console output)
            display_title = "{0} of {1}: {2}".format(curr_item, total_items, createShowTitle(item, args.originaltitle))
            curr_item += 1  # Count the file

            # If the output directory is set then check if it exists and create it if it is not
            # pre-pend it to the file name then
            if args.output is not None:
                if not os.path.exists(args.output):
                    os.makedirs(args.output)
                # Now prepend the directory to the filename
                local_filename = os.path.join(args.output, local_filename)

            #############################################
            # First download the URL for the listing
            ep_graphdata = (
                '?operationName=getProgramType&variables={"id":'
                + str(item["sid"])
                + ',"episodeId":["'
                + str(item["pid"])
                + '"]}&extensions={"persistedQuery":{"version":1,"sha256Hash":"9d18a07f82fcd469ad52c0656f47fb8e711dc2436983b53754e0c09bad61ca29"}}'
            )
            data = requestsVodDataRetrieveWithRetries(ep_graphdata)
            if data is None or len(data) < 1:
                print(
                    "Error: Could not retrieve episode download url, unable to download VOD details, skipping "
                    + item["title"]
                )
                continue

            if (
                not data
                or not "data" in data
                or not "Program" in data["data"]
                or not "episodes" in data["data"]["Program"]
                or len(data["data"]["Program"]["episodes"]) < 1
            ):
                print(
                    "Error: Could not retrieve episode download url, VOD did not return any data, skipping "
                    + item["title"]
                )
                continue

            try:
                ep_data = data["data"]["Program"]["episodes"][0]  # First and only item
                item["vod_url"] = getGroup(RE_CAPTURE_VOD_URL, "urlprefix", ep_data["file"])
                item["vod_dlcode"] = getGroup(RE_CAPTURE_VOD_URL, "dlcode", ep_data["file"])
                # if item['vod_url'] is None or len(item['vod_url']) <= 2:
                if item["vod_dlcode"] is None:
                    item["vod_url"] = getGroup(RE_CAPTURE_VOD_URL_ALTERNATE, "urlprefix", ep_data["file"])
                    item["vod_dlcode"] = getGroup(RE_CAPTURE_VOD_URL_ALTERNATE, "dlcode", ep_data["file"])
                    item["vod_alt"] = True

                # If no VOD code can be found then this cannot be downloaded
                if item["vod_dlcode"] is None:
                    print("Error: Could not locate VOD download code in VOD data, skipping " + item["title"])
                    continue

                # The vod-dlcode is the same as the pid from the old tv schedule, remove the last two characters and update
                item["pid"] = item["vod_dlcode"][:-2]

            except:
                print(
                    "Error: Could not retrieve episode download url due to parsing error in VOD data, skipping "
                    + item["title"]
                )
                continue

            # If the file has already been registered as downloaded then don't attempt to re-download
            if not args.force and item["pid"] in previously_recorded:
                print("'{0}' already recorded (pid={1})".format(color_title(display_title), item["pid"]))
                continue

            # Before we attempt to download the file we should make sure we're not accidentally overwriting an existing file
            if not args.force and not args.checklocal:
                # So, check for the existence of a file with the same name, if one is found then attempt to give
                # our new file a different name and check again (append date and time), if still not unique then
                # create file name with guid, if still not unique then fail!
                if not isLocalFileNameUnique(local_filename):
                    # Check with date
                    local_filename = "{0}_{1}.mp4".format(
                        local_filename.split(".mp4")[0], datetime.datetime.now().strftime("%Y-%m-%d")
                    )
                    if not isLocalFileNameUnique(local_filename):
                        local_filename = "{0}_{1}.mp4".format(local_filename.split(".mp4")[0], str(uuid.uuid4()))
                        if not isLocalFileNameUnique(local_filename):
                            print(
                                "Error: unabled to create a local file name for '{0}', check your output folder (pid={1})".format(
                                    color_title(display_title), item["pid"]
                                )
                            )
                            continue

            # If the checklocal option is enabled then we don't want to try to download unless force is set
            if not args.force and args.checklocal and not isLocalFileNameUnique(local_filename):
                # Store the id as already recorded and save to the file
                print(
                    "'{0}' found locally and marked as already recorded (pid={1})".format(
                        color_title(display_title), item["pid"]
                    )
                )
                appendNewPidAndSavePreviouslyRecordedShows(
                    item["pid"], previously_recorded, previously_recorded_file_name
                )
                continue

            #############################################
            # We will rely on ffmpeg to do the playlist download and merging for us
            # the tool is much better suited to this than manually merging as there
            # are always some corruption issues in the merged stream if done in code

            # Get the correct playlist url
            playlist_data = find_m3u8_playlist_url(item, display_title, args.quality)
            if playlist_data is None:
                print(
                    "Error: Could not download show playlist, not found on server. Try requesting a different video quality."
                )
                continue

            # print(playlist_data
            # Now ask FFMPEG to download and remux all the fragments for us
            result = download_m3u8_playlist_using_ffmpeg(
                ffmpegexec,
                playlist_data["url"],
                playlist_data["fragments"],
                local_filename,
                display_title,
                args.keeppartial,
                args.quality,
            )
            if not result is None:
                # if everything was OK then save the pid as successfully downloaded
                appendNewPidAndSavePreviouslyRecordedShows(
                    item["pid"], previously_recorded, previously_recorded_file_name
                )

    finally:
        deinit()  # Deinitialize the colorama library


if __name__ == "__main__":
    main()

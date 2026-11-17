############################################################################
# Copyright (C) 2024 gempa GmbH                                            #
#                                                                          #
# All Rights Reserved.                                                     #
#                                                                          #
# NOTICE: All information contained herein is, and remains                 #
# the property of gempa GmbH and its suppliers, if any. The intellectual   #
# and technical concepts contained herein are proprietary to gempa GmbH    #
# and its suppliers.                                                       #
# Dissemination of this information or reproduction of this material       #
# is strictly forbidden unless prior written permission is obtained        #
# from gempa GmbH.                                                         #
############################################################################


from datetime import datetime, timedelta
import re
from lib import utils

from lib.const import DEFAULT_NEWS_DATE_FORMAT, DEFAULT_NEWS_DELTA


class News:
    def __init__(self, config):
        self.config = config
        self.pattern = r"\[(\d+)\]\[([\w\s,]+)\]"

    def getNews(self, localCache):
        try:
            response = utils.getNewsFromUrl(self.config.verify)
            if not response:
                return True

            installed_packages = localCache.getIndex()

            current_date = datetime.now().date()
            past_limit = current_date - timedelta(days=DEFAULT_NEWS_DELTA)
            future_limit = current_date + timedelta(days=DEFAULT_NEWS_DELTA)

            relevant_entries = []

            entry_date = None
            entry_text = []

            for line in response.split("\n"):
                line = line.strip()
                if line.startswith("["):
                    matches = re.search(self.pattern, line)
                    if entry_date and entry_text:
                        if past_limit <= entry_date <= future_limit:
                            relevant_entries.append((entry_date, entry_text))
                    if matches:
                        # the text after "[date][packages]" belongs to this entry, and to no
                        # other one if none of the packages is installed
                        entry_date = None
                        result_array_date = matches.group(1)
                        result_array_packages = matches.group(2).split(",")
                        for pkg in result_array_packages:
                            if pkg in installed_packages:
                                entry_date = datetime.strptime(
                                    result_array_date, DEFAULT_NEWS_DATE_FORMAT
                                ).date()
                    else:
                        entry_date = datetime.strptime(
                            line.strip("[]"), DEFAULT_NEWS_DATE_FORMAT
                        ).date()

                    entry_text = []
                else:
                    entry_text.append(line)

            if entry_date and entry_text and past_limit <= entry_date <= future_limit:
                relevant_entries.append((entry_date, entry_text))

            for entryDate in relevant_entries:
                print(f"{entryDate[0]}:")
                for entryNews in entryDate[1]:
                    print(f"         {entryNews}")
        except Exception:
            pass

        return True

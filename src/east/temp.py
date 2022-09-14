import requests
import os
import subprocess
import sys

from rich.progress import Progress

file_url = "https://github.com/NordicSemiconductor/pc-nrfconnect-toolchain-manager/blob/main/resources/nrfutil-toolchain-manager/linux/nrfutil-toolchain-manager.exe?raw=true"

# def copy_url(task_id: TaskID, url: str, path: str) -> None:
#     """Copy data from a url to a local file."""
#     progress.console.log(f"Requesting {url}")
#     response = urlopen(url)
#     # This will break if the response doesn't contain content length
#     progress.update(task_id, total=int(response.info()["Content-length"]))
#     with open(path, "wb") as dest_file:
#         progress.start_task(task_id)
#         for data in iter(partial(response.read, 32768), b""):
#             dest_file.write(data)
#             progress.update(task_id, advance=len(data))
#             if done_event.is_set():
#                 return
#     progress.console.log(f"Downloaded {path}")

# def main():

# file_size = requests.head(file_url, allow_redirects=True).headers.get(
#     "content-length", -1
# )
# response = requests.get(file_url, stream=True)
# print("File size is", file_size)

# with Progress() as progress:
#     task_id = progress.add_task("[red]Downloading...", total=int(file_size))

#     with open("ntm.out", "wb") as ntm:
#         for chunk in response.iter_content(chunk_size=1024):

#             # writing one chunk at a time to pdf file
#             if chunk:
#                 progress.update(task_id, advance=len(chunk))
#                 ntm.write(chunk)

# print("Hello main")

# subprocess.run()

import argparse
import json
import logging
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict, cast

import requests
from prettytable import PrettyTable
from rich.live import Live
from rich.table import Table
from urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter("ignore", InsecureRequestWarning)  # 只忽略 InsecureRequestWarning
# requests.packages.urllib3.disable_warnings()

stop_event = threading.Event()

sourceUrl = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?_="
sourceUrl_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do?vpn-12-o2-xk.bit.edu.cn&_="

infoPage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do"
infoPage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkHome/loadPublicInfo_course.do?vpn-12-o2-xk.bit.edu.cn"

OutPlanCoursePage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?_="
OutPlanCoursePage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadGxkCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_="

InPlanCoursePage = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?_="
InPlanCoursePage_vpn = "https://webvpn.bit.edu.cn/https/77726476706e69737468656265737421e8fc0f9e2e2426557a1dc7af96/yjsxkapp/sys/xsxkappbit/xsxkCourse/loadJhnCourseInfo.do?vpn-12-o2-xk.bit.edu.cn&_="

OutPlanCoursePath = "./OutPlanCourses.json"
InPlanCoursePath = "./InPlanCourses.json"

# ================================= 手动添加课程信息 ================================
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Cookie": "",
}


class CourseInfo(TypedDict):
    bjdm: str
    lx: str
    csrfToken: str  # auto detect


# add class info here
# this is examples
# you can copy it and change bjdm to your course
juzhen_zgc01_data: CourseInfo = {
    "bjdm": "20231-17-1700002-1688866107858",
    "lx": "0",  # 计划内0 / 计划外1
    "csrfToken": "",
}

courseList: List[CourseInfo] = [
    # juzhen_zgc01_data
    # add class info struct here
]
# ================================================================================


class StatusInfo(TypedDict):
    bjmc: str
    success: int
    fail: int


status: Dict[str, StatusInfo] = {}


def printErr(string: str):
    print("\033[31m" + string + "\033[0m")


def printOK(string: str):
    print("\033[32m" + string + "\033[0m")


def setVPN():
    global sourceUrl, infoPage, InPlanCoursePage, OutPlanCoursePage
    sourceUrl = sourceUrl_vpn
    infoPage = infoPage_vpn
    InPlanCoursePage = InPlanCoursePage_vpn
    OutPlanCoursePage = OutPlanCoursePage_vpn


def is_valid_json(json_str: str):
    try:
        json.loads(json_str)
        return True
    except json.JSONDecodeError as e:
        printErr("[-] Fail to catch courses. ERROR:" + str(e))
        return False


def postData(reqCourseList: str, req_data: Dict[str, str | int]):
    try:
        res = requests.post(url=reqCourseList, data=req_data, headers=headers, verify=False)
        res.raise_for_status()
        return res
    except requests.exceptions.HTTPError as errh:
        printErr("[-] Fail to catch courses. HTTP ERROR:" + str(errh))
    except requests.exceptions.ConnectionError as errc:
        printErr("[-] Fail to catch courses. Connection ERROR:" + str(errc))
    except requests.exceptions.Timeout as errt:
        printErr("[-] Fail to catch courses. Timeout ERROR:" + str(errt))
    except requests.exceptions.RequestException as err:
        printErr("[-] Fail to catch courses. Unknown ERROR:" + str(err))

    return None


def getCourseList():
    req_data: Dict[str, int | str] = {
        "query_keyword": "",
        "query_kkyx": "",
        "query_sfct": "",
        "query_sfym": "",
        "fixedAutoSubmitBug": "",
        "pageIndex": 1,
        "pageSize": 1000,
        "sortField": "",
        "sortOrder": "",
    }

    print("[*] Try to catch courses out of plan...")

    timestamp = int(round(time.time() * 1000))
    reqCourseList = OutPlanCoursePage + str(timestamp)

    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)

    with open(OutPlanCoursePath, "w", encoding="utf8") as f:
        f.write(res.text)
    print("[+] Success. Courses have been saved in " + OutPlanCoursePath)

    print("[*] Try to catch courses in plan...")

    timestamp = int(round(time.time() * 1000))
    reqCourseList = InPlanCoursePage + str(timestamp)

    res = postData(reqCourseList, req_data)
    if not res:
        exit(1)
    if not is_valid_json(res.text):
        exit(1)

    with open(InPlanCoursePath, "w", encoding="utf8") as f:
        f.write(res.text)
    print("[+] Success. Courses have been saved in " + InPlanCoursePath)


def findCourse(idList: List[str], XQMC: str):
    with open(InPlanCoursePath, "r", encoding="utf8") as f:
        InPlanCourseInfoFile = f.read()
    InPlanCourseInfo = json.loads(InPlanCourseInfoFile)
    with open(OutPlanCoursePath, "r", encoding="utf8") as f:
        OutPlanCourseInfoFile = f.read()
    OutPlanCourseInfo = json.loads(OutPlanCourseInfoFile)

    targetList: List[List[str]] = []
    for id in idList:
        print("[*] Looking for course id:", id, "...")
        for info in InPlanCourseInfo["datas"]:
            if id == info["KCDM"] and info["XQMC"] == XQMC and ("非全" not in info["BJMC"]):
                targetList.append([info["BJMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({"bjdm": info["BJDM"], "lx": "0", "csrfToken": ""})
                status[info["BJDM"]] = {"bjmc": info["BJMC"], "success": 0, "fail": 0}
        for info in OutPlanCourseInfo["datas"]:
            if id == info["KCDM"] and info["XQMC"] == XQMC and ("非全" not in info["BJMC"]):
                targetList.append([info["BJMC"], info["RKJS"], "{}/{}".format(info["DQRS"], info["KXRS"])])
                courseList.append({"bjdm": info["BJDM"], "lx": "1", "csrfToken": ""})
                status[info["BJDM"]] = {"bjmc": info["BJMC"], "success": 0, "fail": 0}

    for course in courseList:
        # 前面手动添加的课程信息，在信息中搜索
        if course["bjdm"] not in status:
            searched = (
                c
                if (
                    c := next((info for info in InPlanCourseInfo["datas"] if info["BJDM"] == course["bjdm"]), None)
                    is not None
                )
                else next((info for info in OutPlanCourseInfo["datas"] if info["BJDM"] == course["bjdm"]), None)
            )
            if searched is not None:
                searched = cast(Dict[str, str], searched)
                targetList.append(
                    [searched["BJMC"], searched["RKJS"], "{}/{}".format(searched["DQRS"], searched["KXRS"])]
                )
                status[course["bjdm"]] = {"bjmc": searched["BJMC"], "success": 0, "fail": 0}
            else:
                # 没搜索到，姑且还是添加进来进行请求，未测试可行性
                status[course["bjdm"]] = {"bjmc": course["bjdm"], "success": 0, "fail": 0}

    if len(targetList) == 0:
        print("[!] No course found according to course id.")
        if len(courseList) == 0:
            print("[!] No course need to be chosen.")
            exit(0)
    else:
        table = PrettyTable()
        table.field_names = ["Name", "Teachers", "Chosen"]
        table.align["Name"] = "l"  # type: ignore
        table.add_rows(targetList)  # type: ignore
        print("[+] Target courses showm as follow:")
        print(table)


def chooseCourse(course: CourseInfo):
    while not stop_event.is_set():
        timestamp = int(round(time.time() * 1000))
        courseUrl = sourceUrl + str(timestamp)
        res = requests.post(url=courseUrl, data=course, headers=headers, verify=False)
        res = json.loads(res.text)
        if res["code"] == 1:
            printOK(f"[+] A course is chosen! You can see on Web Browser! [{status[course['bjdm']]['bjmc']}]")
            status[course["bjdm"]]["success"] += 1
        else:
            logging.debug(res)
            status[course["bjdm"]]["fail"] += 1
        time.sleep(0.01)


def make_status_table():
    table = Table(title="Status")
    table.add_column("Name", justify="center")
    table.add_column("S", justify="center")
    table.add_column("F", justify="center")

    for _, s in status.items():
        table.add_row(s["bjmc"], str(s["success"]), str(s["fail"]))
    return table


def start():
    print("[*] Start race...Please wait for servel hours...")
    with ThreadPoolExecutor(max_workers=len(courseList)) as pool:
        for course in courseList:
            pool.submit(chooseCourse, course)

        heartbeat = 0
        live = Live(make_status_table(), refresh_per_second=2)
        live.start()
        try:
            while not stop_event.is_set():
                if heartbeat % 30 == 0:
                    try:
                        res = requests.get(url=infoPage, headers=headers, verify=False)
                        csrfToken = json.loads(res.text)["csrfToken"]
                        for course in courseList:
                            course["csrfToken"] = csrfToken
                    except Exception as e:
                        print(f"[ERROR] refresh token failed: {e}")

                live.update(make_status_table())
                time.sleep(2)
                heartbeat += 1
        except KeyboardInterrupt:
            print("[*] Ctrl+C pressed, stopping all threads...")
            stop_event.set()
        finally:
            live.stop()


if __name__ == "__main__":

    @dataclass
    class Args:
        cookie: str
        courseID: Optional[List[str]]
        vpn: bool
        liangxiang: bool
        debug: bool

    parser = argparse.ArgumentParser(description="BIT Course Race. A script to help masters get courses.")
    parser.add_argument(
        "-c",
        "--cookie",
        type=str,
        required=True,
        dest="cookie",
        help="Cookie copied from your web browser(after logging in sucessfully)",
    )
    parser.add_argument(
        "-i", "--courseID", type=str, dest="courseID", nargs="+", help="ID of courses, split with space"
    )
    parser.add_argument(
        "-v", "--vpn", dest="vpn", action="store_true", help="if you choose course through webvpn, then use this"
    )
    parser.add_argument(
        "-l", "--liangxiang", dest="liangxiang", action="store_true", help="switch campuses to Liangxiang campuses"
    )
    parser.add_argument(
        "-d", "--debug", dest="debug", action="store_true", help="if you want to show debug messages, then use this"
    )
    parsed = parser.parse_args()
    args: Args = Args(
        cookie=parsed.cookie, courseID=parsed.courseID, vpn=parsed.vpn, liangxiang=parsed.liangxiang, debug=parsed.debug
    )

    headers["Cookie"] = args.cookie

    if args.vpn is True:
        setVPN()

    if args.debug is True:
        logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    else:
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    getCourseList()

    findCourse(
        args.courseID if args.courseID else [],
        "良乡校区" if args.liangxiang else "中关村校区",
    )

    start()

    # res = requests.get(url=infoPage, headers=headers, verify=False)
    # csrfToken = json.loads(res.text)['csrfToken']
    # for course in courseList:
    #     course['csrfToken'] = csrfToken

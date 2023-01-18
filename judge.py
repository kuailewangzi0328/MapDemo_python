import pathlib
import pandas as pd
import json
import pypinyin
import re
import cn2an

cityMap = None
tibetNameList = None


# 初始化西藏地区行政区域数组
def prepareTibetCityMap() -> json:
    path = pathlib.Path("asset/tibetCityMap.json")
    with open(str(path)) as jsonFile:
        return json.load(jsonFile)


# 初始化西藏常见姓名数组
def prepareTibetNameList() -> json:
    path = pathlib.Path("asset/tibetName.json")
    with open(str(path)) as jsonFile:
        return json.load(jsonFile)


# 填充"判决机关所在地市/县区"
def fillCourtCityDistrict(data: json):
    address: str = data["判决机关"].replace("西藏自治区", "").replace("西藏", "")
    for city in cityMap:
        cityName: str = city["name"].replace("市", "").replace("地区", "")
        if address.__contains__(cityName):  # 当前值包含特定市名称，直接设置市名
            data["判决机关所在地市"] = city["name"]
        for district in city["subCity"]:
            districtName: str = district.replace("县", "").replace("区", "")
            if address.__contains__(districtName):  # 当前值包含特定县区名称，设置县名，并填充对应市名
                data["判决机关所在县区"] = district
                data["判决机关所在地市"] = city["name"]


# 填充"案号缩写新",值来自旧案号修改
def fillCaseNo(data: json):
    caseNoStr: str = data["案号"]
    oldNo: str = data["案号缩写旧"]
    data["案号缩写新"] = oldNo
    index = caseNoStr.find("）")
    if index != -1 and str(caseNoStr[index + 1]) != "藏" and oldNo.__contains__("z"):
        pinyin = pypinyin.pinyin(str(caseNoStr[index + 1]), style=pypinyin.NORMAL)
        firstPy = pinyin[0][0][0]
        # print(pinyin)
        # print(firstPy)
        data["案号缩写新"] = oldNo.replace("z", firstPy)


# 填充辩护人信息
def fillLawyer(data: json):
    lawyerDesc: str = data["是否请辩护人"]
    if lawyerDesc.startswith("否"):
        data["辩护人"] = "无"
    elif lawyerDesc.startswith("是"):
        if lawyerDesc.__contains__("司法局"):
            data["辩护人"] = "司法指定"
        elif lawyerDesc.__contains__("辩护人"):
            data["辩护人"] = "自请"
        else:
            data["辩护人"] = "未知"
    else:
        data["辩护人"] = "未知"


# 填充被告人户籍县市信息
def fillCulpritHomeInfo(data: json):
    culpritHomeDesc: str = data["被告人户籍"]
    if culpritHomeDesc.__contains__("未显示"):
        data["被告人所在市"] = "未知"
        data["被告人所在县"] = "未知"
    else:
        homeAddress = culpritHomeDesc.replace("西藏自治区", "").replace("西藏", "")
        homeInTibet = False
        for city in cityMap:
            needBreak = False
            cityName: str = city["name"].replace("市", "").replace("地区", "")
            if homeAddress.__contains__(cityName):  # 当前值包含特定市名称，直接设置市名
                data["被告人所在市"] = cityName
                homeInTibet = True
            for district in city["subCity"]:
                districtName: str = district.replace("县", "").replace("区", "")
                if homeAddress.__contains__(districtName):  # 当前值包含特定县区名称，设置县名，并填充对应市名
                    data["被告人所在市"] = cityName
                    data["被告人所在县"] = district
                    homeInTibet = True
                    needBreak = True
                    break
            if needBreak:
                break
        if not homeInTibet:
            data["被告人所在市"] = "内地"
            data["被告人所在县"] = "内地"


# 格式化赔偿金额数字
def fillMoneyNum(data: json):
    moneyDesc: str = data["谅解协议赔偿数额"]
    if moneyDesc is not None:
        if moneyDesc.__contains__("(") or moneyDesc.__contains__("（"):
            index = moneyDesc.find("(")
            if index == -1:
                index = moneyDesc.find("（")
            moneyDesc = moneyDesc[0:index]
        if moneyDesc.__contains__("元"):
            moneyNumStr = moneyDesc.replace(" ", "").replace(",", "").replace("，", "")
            moneyNum = 0
            if moneyNumStr.__contains__("万元"):
                moneyNumStr = moneyNumStr.replace("万元", "")
                if moneyNumStr.__contains__("."):  # 转小数
                    moneyNum = int(float(moneyNumStr) * 10000)
                else:  # 转整数
                    # print("当前需要转化的数字为：" + moneyNumStr)
                    moneyNum = int(cn2an.cn2an(moneyNumStr, "smart")) * 10000
            else:
                # print("当前需要转化的数字为：" + moneyNumStr)
                moneyNumStr = moneyNumStr.replace("元", "").replace("余", "").replace("多", "")
                moneyNum = int(cn2an.cn2an(moneyNumStr, "smart"))
            data["赔偿数额格式化"] = moneyNum
        else:
            data["赔偿数额格式化"] = moneyDesc
    else:
        data["赔偿数额格式化"] = "未赔偿"


# 判断姓名是否包含常见藏语名称
def checkIfNameIsTibet(name: str) -> bool:
    for tibetName in tibetNameList:
        if name.__contains__(tibetName):
            return True
    else:
        return False


# 填充审判长姓名及民族
def fillJudgeNameAndNation(data: json):
    judgeInfoDesc: str = data["法官或合议庭民族"]
    if judgeInfoDesc.startswith("审判"):
        tempJudgeDesc = judgeInfoDesc[2:len(judgeInfoDesc)]
        if tempJudgeDesc.__contains__(",") or tempJudgeDesc.__contains__("，") or tempJudgeDesc.__contains__(
                "审判") or tempJudgeDesc.__contains__("书记") or tempJudgeDesc.__contains__(
            "法官") or tempJudgeDesc.__contains__("人民"):
            indexList = []
            secondJudgeIndex = 999
            if tempJudgeDesc.find("审判") != -1:
                indexList.append(tempJudgeDesc.find("审判"))
            if tempJudgeDesc.find("书记") != -1:
                indexList.append(tempJudgeDesc.find("书记"))
            if tempJudgeDesc.find("法官") != -1:
                indexList.append(tempJudgeDesc.find("法官"))
            if tempJudgeDesc.find("人民") != -1:
                indexList.append(tempJudgeDesc.find("人民"))
            if tempJudgeDesc.find(",") != -1:
                indexList.append(tempJudgeDesc.find(","))
            if tempJudgeDesc.find("，") != -1:
                indexList.append(tempJudgeDesc.find("，"))

            for index in indexList:
                if index < secondJudgeIndex:
                    secondJudgeIndex = index

            judgeNameDesc = "审判" + tempJudgeDesc[0:secondJudgeIndex]
            judgeName = judgeNameDesc.replace("审判长", "").replace("审判员", "").replace(",", "").replace("，", "")
            isTibetName = checkIfNameIsTibet(judgeName)
            # if not isTibetName:
            #     print("当前判断得到的审判长姓名为：" + judgeName + " 非藏族")
            data["审判长姓名"] = judgeName
            if isTibetName:
                data["审判长民族"] = "藏"
            else:
                data["审判长民族"] = "汉"


# 对特定数据格式做优化
def formatData(row: dict):
    isBaoLi: str = row["前科是否是八种暴力性犯罪"]
    if isBaoLi is None:
        row["前科是否是八种暴力性犯罪"] = "未知"
    elif len(isBaoLi) > 1:
        row["前科是否是八种暴力性犯罪"] = isBaoLi[0]

    for key, value in row.items():
        if str(value).__contains__("未显示") or value is None:
            row[key] = "未知"


# 计算被告人人数并根据人数排序
def calcCulpritNumAndSort(originDataJsonArray: list):
    # 计算人数
    for data in originDataJsonArray:
        culpritDesc: str = data["被告人"]
        culpritList = re.split("，|,", culpritDesc)
        data["被告人人数"] = len(culpritList)
    # 根据人数排序
    # print("总条数：" + len(originDataJsonArray).__str__())
    multipleCulpritDataList = []
    for data in originDataJsonArray:
        culpritNum = data["被告人人数"]
        if culpritNum > 1:
            multipleCulpritDataList.append(data)
    for data in multipleCulpritDataList:
        originDataJsonArray.remove(data)
    # print("单被告条数：" + len(originDataJsonArray).__str__())
    # print("多被告条数：" + len(multipleCulpritDataList).__str__())
    multipleCulpritDataList.sort(key=lambda x: x["被告人人数"])
    return multipleCulpritDataList


# 拆分多被告数据为多条
def splitMultipleCulpritData(multipleCulpritDataList):
    newDataList = []
    for data in multipleCulpritDataList:
        culpritList = re.split("，|,", data["被告人"].replace(" ", ""))
        culpritNationList = re.split("，|,", data["被告人民族"].replace(" ", ""))
        culpritHomeList = re.split("，|,", data["被告人户籍"].replace(" ", ""))
        culpritGenderList = re.split("，|,", data["被告人性别"].replace(" ", ""))
        culpritAgeList = re.split("，|,", data["被告人年龄"].replace(" ", ""))
        culpritResultList = re.split("，|,", data["判处结果"].replace(" ", ""))
        culpritIsZiShouList = re.split("，|,", data["是否自首"].replace(" ", ""))
        culpritIsLiGongList = re.split("，|,", data["是否立功"].replace(" ", ""))
        culpritIsTanBaiList = re.split("，|,", data["是否坦白"].replace(" ", ""))
        culpritIsCongFanList = re.split("，|,", data["是否从犯"].replace(" ", ""))
        culpritIsRenZuiList = re.split("，|,", data["是否认罪"].replace(" ", ""))
        culpritIsHuaiYunList = re.split("，|,", data["是否怀孕"].replace(" ", ""))
        culpritIsCanRenList = re.split("，|,", data["是否特别残忍"].replace(" ", ""))
        culpritIsGongKaiList = re.split("，|,", data["是否公开场合行凶"].replace(" ", ""))
        culpritIsXiongQiList = re.split("，|,", data["是否使用凶器"].replace(" ", ""))
        culpritIsChuFanList = re.split("，|,", data["是否初犯偶犯"].replace(" ", ""))
        culpritIsLeiFanList = re.split("，|,", data["是否构成累犯"].replace(" ", ""))
        culpritIsBaoLiList = re.split("，|,", data["前科是否是八种暴力性犯罪"].replace(" ", "")) \
            if data["前科是否是八种暴力性犯罪"] is not None else [" "]
        culpritIsGuoCuoList = re.split("，|,", data["被害人是否有过错"].replace(" ", ""))
        culpritIsLiangJieList = re.split("，|,", data["是否积极赔偿被害人损失并取得刑事谅解"].replace(" ", ""))

        for index, culpritName in enumerate(culpritList):
            culpritInfo = {}
            culpritInfo["判决书"] = data["判决书"]
            culpritInfo["判决机关"] = data["判决机关"]
            culpritInfo["判决机关所在地市"] = data["判决机关所在地市"]
            culpritInfo["判决机关所在县区"] = data["判决机关所在县区"]
            culpritInfo["案号"] = data["案号"]
            culpritInfo["案号缩写旧"] = data["案号缩写旧"]
            culpritInfo["案号缩写新"] = data["案号缩写新"]
            culpritInfo["判决日期"] = data["判决日期"]
            culpritInfo["判决年份"] = data["判决年份"]
            culpritInfo["是否请辩护人"] = data["是否请辩护人"]
            culpritInfo["辩护人"] = data["辩护人"]
            culpritInfo["被告人"] = culpritName
            culpritInfo["被告人人数"] = str(data["被告人人数"]) + "-" + str(index + 1)
            culpritInfo["被告人所在市"] = data["被告人所在市"]
            culpritInfo["被告人所在县"] = data["被告人所在县"]
            culpritInfo["被害人伤残等级"] = data["被害人伤残等级"]
            culpritInfo["谅解协议赔偿数额"] = data["谅解协议赔偿数额"]
            culpritInfo["赔偿数额格式化"] = data["赔偿数额格式化"]
            culpritInfo["法官或合议庭民族"] = data["法官或合议庭民族"]
            culpritInfo["审判长姓名"] = data["审判长姓名"]
            culpritInfo["审判长民族"] = data["审判长民族"]

            culpritInfo["被告人民族"] = culpritNationList[index if len(culpritNationList) > index else 0]
            culpritInfo["被告人户籍"] = culpritHomeList[index if len(culpritHomeList) > index else 0]
            culpritInfo["被告人性别"] = culpritGenderList[index if len(culpritGenderList) > index else 0]
            culpritInfo["被告人年龄"] = culpritAgeList[index if len(culpritAgeList) > index else 0]
            culpritInfo["判处结果"] = culpritResultList[index if len(culpritResultList) > index else 0]
            culpritInfo["是否自首"] = culpritIsZiShouList[index if len(culpritIsZiShouList) > index else 0]
            culpritInfo["是否立功"] = culpritIsLiGongList[index if len(culpritIsLiGongList) > index else 0]
            culpritInfo["是否坦白"] = culpritIsTanBaiList[index if len(culpritIsTanBaiList) > index else 0]
            culpritInfo["是否从犯"] = culpritIsCongFanList[index if len(culpritIsCongFanList) > index else 0]
            culpritInfo["是否认罪"] = culpritIsRenZuiList[index if len(culpritIsRenZuiList) > index else 0]
            culpritInfo["是否怀孕"] = culpritIsHuaiYunList[index if len(culpritIsHuaiYunList) > index else 0]
            culpritInfo["是否特别残忍"] = culpritIsCanRenList[index if len(culpritIsCanRenList) > index else 0]
            culpritInfo["是否公开场合行凶"] = culpritIsGongKaiList[index if len(culpritIsGongKaiList) > index else 0]
            culpritInfo["是否使用凶器"] = culpritIsXiongQiList[index if len(culpritIsXiongQiList) > index else 0]
            culpritInfo["是否初犯偶犯"] = culpritIsChuFanList[index if len(culpritIsChuFanList) > index else 0]
            culpritInfo["是否构成累犯"] = culpritIsLeiFanList[index if len(culpritIsLeiFanList) > index else 0]
            culpritInfo["前科是否是八种暴力性犯罪"] = culpritIsBaoLiList[
                index if len(culpritIsBaoLiList) > index else 0][0].replace(" ", "")
            culpritInfo["被害人是否有过错"] = culpritIsGuoCuoList[index if len(culpritIsGuoCuoList) > index else 0]
            culpritInfo["是否积极赔偿被害人损失并取得刑事谅解"] = culpritIsLiangJieList[
                index if len(culpritIsLiangJieList) > index else 0]

            newDataList.append(culpritInfo)
    return newDataList


# 保存新数据到excel
def saveDataToExcel(resultDF):
    path = pathlib.Path("asset/西藏案件量刑数据(修复版本).xlsx")
    if path.exists():
        path.unlink()
    resultDF.to_excel(str(path), sheet_name='故意伤害罪', index=False)


def modifyData():
    global cityMap
    global tibetNameList
    cityMap = prepareTibetCityMap()
    tibetNameList = prepareTibetNameList()
    # print(cityMap)
    # print(tibetNameList)
    # path = pathlib.Path("asset/西藏案件量刑数据(缩略版本).xlsx")
    path = pathlib.Path("asset/西藏案件量刑数据(完整版本).xlsx")
    originDataFrame = pd.read_excel(str(path), sheet_name="故意伤害罪")  # 读取原始数据
    originDataJsonArray: list = json.loads(originDataFrame.to_json(orient="records", force_ascii=False))  # 转成json格式

    multipleCulpritDataList = calcCulpritNumAndSort(originDataJsonArray)  # 计算被告人人数并根据人数排序
    originDataJsonArray.extend(splitMultipleCulpritData(multipleCulpritDataList))  # 拆分多被告数据为多条

    for row in originDataJsonArray:
        fillCourtCityDistrict(row)  # 处理判决地市县
        fillCaseNo(row)  # 处理案号缩写
        fillLawyer(row)  # 处理辩护人
        fillCulpritHomeInfo(row)  # 处理被告人户籍县市数据
        fillMoneyNum(row)  # 处理赔偿金额
        fillJudgeNameAndNation(row)  # 处理审判长姓名及民族信息
        formatData(row)  # 处理特定数据格式
    # print(originDataJsonArray)
    resultDF = pd.json_normalize(originDataJsonArray)  # 转回dataFrame
    saveDataToExcel(resultDF)


if __name__ == '__main__':
    modifyData()

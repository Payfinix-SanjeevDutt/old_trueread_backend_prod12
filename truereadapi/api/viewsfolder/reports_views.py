from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from ..models import Consumers, MeterReaderRegistration, Office
from ..serializers import MeterReaderRegistrationSerializer, ConsumerDataSerializer, ConsumerWiseDetailsSerializer, MridSerializer, Serail
from django.db.models import Q
from rest_framework import status
import datetime
from ..serializers import ConsumerSerializer
from rest_framework.decorators import parser_classes

from rest_framework.parsers import MultiPartParser, FormParser
from django.db import connection
import json
import jwt
from django.contrib.auth import authenticate
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination

from django.http import JsonResponse
from django.db.models import Count, Case, When, IntegerField
# from decouple import config
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.core.paginator import Paginator
import base64
from datetime import datetime, timedelta, date
from copy import deepcopy
import math
from rest_framework.views import APIView
from rest_framework.response import Response
from openpyxl import Workbook
from django.http import HttpResponse
from django.forms.models import model_to_dict


# ############################################################################# #
def dictfetchall(cursor):

    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


# # OCR Accuracy Report- UPDATE of 1st table
@api_view(['POST'])
def getocraccuracydata(request):
    new = []
    def listfun(dict):
        new.append(dict.copy())
        return new
    newdict = {}
    cursor = connection.cursor()
    pagesize = request.query_params.get('pagesize', None)
    dates = request.data.get('month', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    agency = request.data.get('agency', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    paginator=PageNumberPagination()

    clause = 'WHERE '
    clause1 = ' '
    clause += f"extract(month from reading_date_db) = '{dates.split('-')[1]}' AND extract(year from reading_date_db) = '{dates.split('-')[0]} ' " if (
        dates) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f" AND bl_agnc_name in ('Fluent Grid','Fluentgrid') "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') "
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    # str1 = f" AND bl_agnc_name='{agency}'" if (agency) else ''
    clause += str1
    clause1 +=str1         

    str2 = f"AND {locationWise} ='{locationName}'" if (locationName) else ''
    clause += str2
    clause1+=str2

    query = f'''
    with current_month as (
    select m.{groupby} as location,count(m.mr_id)as mrid,
    count(m.prsnt_mtr_status='Ok' or null) as curok, count(m.prsnt_mtr_status='Meter Defective' or null) as curmd,
    count(m.prsnt_mtr_status='Door Locked' or null) as curdl,count(m.rdng_ocr_status='Passed' or null) as curpassed,
    count(m.rdng_ocr_status='Failed' or null) as curfailed from readingmaster m left JOIN meterreaderregistration o ON m.mr_id=o."mrId"
    {clause}   group by m.{groupby}
        ),
    prev_month as (SELECT {groupby} as location, COUNT( r.prsnt_mtr_status='Ok' or null ) AS prevok,
  COUNT( r.rdng_ocr_status='Passed' or null) AS prevpassed FROM readingmaster r left JOIN meterreaderregistration o ON r.mr_id=o."mrId"
    where reading_date_db >= date_trunc('month', '{(dates+'-01') if(dates) else date.today()}'::date - interval '1' month)
        and reading_date_db < date_trunc('month', '{(dates+'-01') if(dates) else date.today()}'::date) {clause1} group by {groupby})

    select current_month.location, current_month.mrid,
    current_month.curok, current_month.curmd,
    current_month.curdl, current_month.curpassed, current_month.curfailed,
    prev_month.prevpassed, prev_month.prevok from current_month full join prev_month on current_month.location=prev_month.location where current_month.location!='' 
    '''
    print(query)
    cursor.execute(query)
    results = cursor.fetchall()
    # count = 0
    try:
        for row in results:
            total = row[1]
            okreadings = row[2]
            meterdefective = row[3]
            doorlocked = row[4]
            ocrpassed = row[5]
            ocrwithexcep = row[6]
            previousmonthPassed = row[7]
            previousmonthOk = row[8]
            ocrreadingpercent = math.floor(
                (((ocrpassed/okreadings) if okreadings else 0)*100))
            lastmonthaccuracy =math.floor(
                (((previousmonthPassed/previousmonthOk) if previousmonthOk else 0)*100))

            # add to dictionary
            newdict['locationname'] = row[0]
            newdict['totalReadings'] = row[1]
            newdict['ok'] = okreadings
            newdict['OCRpassed'] = ocrpassed
            newdict['OCRaccuracy'] = ocrreadingpercent
            newdict['OCRwithException'] = ocrwithexcep
            newdict['MeterDefective'] = meterdefective
            newdict['DoorLocked'] = doorlocked
            newdict['lastmonth'] = str(lastmonthaccuracy)
            # newdict['prevok'] = row[8]
            # newdict['prevpassed'] = row[7] if row[7] else 0
            # newdict['prevok'] = row[8] if row[8] else 0
            # newdict['DoorLocked'] = row[9]
            newdata = listfun(newdict)
        if pagesize:
            paginator.page_size=pagesize
        else:
            paginator.page_size=17000
        res_page=paginator.paginate_queryset(newdata, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("ex", str(e))
        return Response([])


# MR Wise Accuracy Report  - 2nd table - updated

# MR Wise Accuracy Report  - 2nd table - updated
# @api_view(["POST"])
# def getMRwiseAccuracyreport(request):
#     pagesize = request.query_params.get("pagesize", None)  # name of month
#     paginator = PageNumberPagination()
#     dates = request.data.get("month", None)  # name of month
#     locationWise = request.data.get("locationwise", None)  # name of categories
#     groupby = request.data.get("groupby", None)  # name of categories
#     agency = request.data.get("agency", None)  # name of categories
#     locationName = request.data.get("locationname", None)  # category values

#     cursor = connection.cursor()
#     cursorn = connection.cursor()
#     new = []

#     def listfun(dict):
#         # print(dict)
#         new.append(dict.copy())
#         return new

#     clause = "WHERE "
#     clause1 = " "
#     clause += (
#         f"extract(month from reading_date_db) = '{dates.split('-')[1]}' AND extract(year from reading_date_db) = '{dates.split('-')[0]}' "
#         if (dates)
#         else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
#     )
#     str1 = f" AND bl_agnc_name='{agency}'" if (agency) else ""
#     clause += str1
#     clause1 += str1
#     str2 = f"AND {locationWise} ='{locationName}'" if (locationName) else ""
#     clause += str2
#     clause1 += str2

#     newdict = {}
#     newclause = (
#         f"and extract(month from reading_date_db) = '{dates.split('-')[1]}'"
#         if (dates)
#         else f"and extract(month from reading_date_db) = '{date.today().month}'"
#     )
#     import time
#     start = time.time()

#     # query = (f'''SELECT {groupby}, m."mrId" as mrId,  m."mrName" as name,  m."mrPhone" as phone,  count(r.id),  count(r.prsnt_mtr_status='Door Locked' or NULL), count(r.prsnt_mtr_status='Meter Defective' or NULL),
#     #         count(r.prsnt_mtr_status='Ok' or NULL),count(r.rdng_ocr_status='Passed' or NULL), count(r.rdng_ocr_status='Failed' or NULL) from readingmaster r LEFT JOIN meterreaderregistration m ON m."mrId" = r.mr_id {clause} group by {groupby}, m."mrId",m."mrName",m."mrPhone"
#     #         ''')
#     query = f"""
#         SELECT 
#         reader.{groupby},
#         reader.mrId,reader.name,
#         reader.phone,
#         ocr_count.greater,
#         ocr_count.lesser,
#         reader.count_id,
#         reader.count_door_locked,
#         reader.count_meter_defective,
#         reader.count_ok,
#         reader.count_rdng_passed,
#         reader.count_rdng_failed
#         FROM
#         (SELECT
#             greater_counts.mr_id AS mr_id,
#             greater_counts.greater AS greater,
#             lesser_counts.lesser AS lesser
#         FROM
#             (SELECT
#             COUNT(*) AS greater,
#             mr_id
#             FROM
#             readingmaster
#             WHERE
#             prsnt_ocr_rdng ~ '^\d+$'
#             AND prsnt_rdng ~ '^\d+$'
#             AND CAST(prsnt_ocr_rdng AS BIGINT) > CAST(prsnt_rdng AS BIGINT)
#             {newclause}
#             GROUP BY
#             mr_id) AS greater_counts
#         JOIN
#             (SELECT
#             COUNT(*) AS lesser,
#             mr_id
#             FROM
#             readingmaster
#             WHERE
#             prsnt_ocr_rdng ~ '^\d+$'
#             AND prsnt_rdng ~ '^\d+$'
#             AND CAST(prsnt_ocr_rdng AS BIGINT) < CAST(prsnt_rdng AS BIGINT)
#             {newclause}
#             GROUP BY mr_id) AS lesser_counts ON greater_counts.mr_id = lesser_counts.mr_id) AS ocr_count
#         JOIN
#         (SELECT 
#             {groupby},
#             m."mrId" AS mrId,
#             m."mrName" AS name,
#             m."mrPhone" AS phone,
#             count(r.id) AS count_id,
#             count(r.prsnt_mtr_status = 'Door Locked' OR NULL) AS count_door_locked,
#             count(r.prsnt_mtr_status = 'Meter Defective' OR NULL) AS count_meter_defective,
#             count(r.prsnt_mtr_status = 'Ok' OR NULL) AS count_ok,
#             count(r.rdng_ocr_status = 'Passed' OR NULL) AS count_rdng_passed,
#             count(r.rdng_ocr_status = 'Failed' OR NULL) AS count_rdng_failed
#         FROM
#             readingmaster r
#         LEFT JOIN
#             meterreaderregistration m ON m."mrId" = r.mr_id
#         {clause}
#         GROUP BY
#             {groupby}, m."mrId", m."mrName", m."mrPhone"
#         ) AS reader
#         ON
#         ocr_count.mr_id = reader.mrId"""

#     lmquery = f"""SELECT {groupby}, r.mr_id, count(r.rdng_ocr_status='Passed' or null), count(r.prsnt_mtr_status='Ok' or null) FROM readingmaster r LEFT JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month','{(dates+'-01') if(dates) else date.today()}'::date - interval '1' month)
#                 and reading_date_db < date_trunc('month', '{(dates+'-01') if(dates) else date.today()}'::date ) {clause1} group by r.mr_id, {groupby}
#             """
#     print(query)
#     cursor.execute(query)
#     results = cursor.fetchall()
#     cursorn.execute(lmquery)
#     lmresults = cursorn.fetchall()

#     lmaccuracy = {}
#     for i in lmresults:
#         passed = i[2]
#         ok = i[3]

#         accuracy = math.floor(((passed / ok) if ok else 0) * 100)
#         lmaccuracy[i[1]] = accuracy

#     count = 0

#     print("total time", time.time()-start)
#     try:
#         for row in results:
#             # print("12")
#             location = str(row[0])
#             mrId = row[1]
#             name = row[2]
#             phone = row[3]
#             greater = row[4]
#             lesser = row[5]
#             total = row[6]
#             doorlocked = row[7]
#             meterdefective = row[8]
#             okreadings = row[9]
#             ocrwithoutexcep = row[10]
#             ocrwithexcep = row[11]
#             # Percentage
#             ocrreadingpercent = math.floor(
#                 (((ocrwithoutexcep / okreadings) if okreadings else 0) * 100)
#             )

#             # add to dictionary
#             newdict["location"] = location
#             newdict["mrid"] = mrId
#             newdict["name"] = name
#             newdict["mobile"] = phone
#             newdict["ocr_greater"] = greater
#             newdict["ocr_lesser"] = lesser
#             newdict["totalReadings"] = total
#             newdict["DoorLocked"] = doorlocked
#             newdict["MeterDefective"] = meterdefective
#             newdict["OK"] = okreadings
#             newdict["OCRwithException"] = ocrwithexcep
#             newdict["OCRwithoutExcep"] = ocrwithoutexcep
#             newdict["OCRReadingspercent"] = ocrreadingpercent
#             if row[1] in lmaccuracy:
#                 newdict["lastmonth"] = lmaccuracy[row[1]]
#                 newdict["incrdectrAccuracy"] = str(
#                     ocrreadingpercent - lmaccuracy[row[1]]
#                 )
#             else:
#                 newdict["lastmonth"] = ""
#                 newdict["incrdectrAccuracy"] = ""

#             count = count + 1
#             # add to list
#             newdata = listfun(newdict)
#         if pagesize:
#             paginator.page_size = pagesize
#         else:
#             paginator.page_size = 17000
#         result_page = paginator.paginate_queryset(newdata, request)
#         return paginator.get_paginated_response(result_page)
#     except:
#         return Response([])

# update for faster quering in db
@api_view(["POST"])
def getMRwiseAccuracyreportfast(request):
    pagesize = request.query_params.get("pagesize", None)  # name of month
    paginator = PageNumberPagination()
    dates = request.data.get("month", None)  # name of month
    locationWise = request.data.get("locationwise", None)  # name of categories
    groupby = request.data.get("groupby", None)  # name of categories
    agency = request.data.get("agency", None)  # name of categories
    locationName = request.data.get("locationname", None)  # category values

    cursor = connection.cursor()
    cursorn = connection.cursor()

    new = []
    def listfun(dict):
        # print(dict)
        new.append(dict.copy())
        return new

    clause = "WHERE "
    clause1 = " "
    clause += (
        f"extract(month from reading_date_db) = '{dates.split('-')[1]}' AND extract(year from reading_date_db) = '{dates.split('-')[0]}' "
        if (dates)
        else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    )
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f" AND bl_agnc_name in ('Fluent Grid','Fluentgrid') "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') "
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    # str1 = f" AND bl_agnc_name='{agency}'" if (agency) else ""
    clause += str1
    clause1 += str1
    str2 = f"AND {locationWise} ='{locationName}'" if (locationName) else ""
    clause += str2
    clause1 += str2

    newdict = {}
    newclause = (
        f"and extract(month from reading_date_db) = '{dates.split('-')[1]}'"
        if (dates)
        else f"and extract(month from reading_date_db) = '{date.today().month}'"
    )
    import time
    start = time.time()

    query = f"""
            SELECT
                r.{groupby},
                r.mr_id AS mrId,
                m."mrName" AS name,
                m."mrPhone" AS phone,
                count(r.id) AS count_id,
                count(r.prsnt_mtr_status = 'Door Locked' OR NULL) AS count_door_locked,
                count(r.prsnt_mtr_status = 'Meter Defective' OR NULL) AS count_meter_defective,
                count(r.prsnt_mtr_status = 'Ok' OR NULL) AS count_ok,
                count(r.rdng_ocr_status = 'Passed' OR NULL) AS count_rdng_passed,
                count(r.rdng_ocr_status = 'Failed' OR NULL) AS count_rdng_failed,
                COUNT(CASE WHEN r.prsnt_ocr_rdng ~ '^\d+$' AND r.prsnt_rdng ~ '^\d+$' AND CAST(r.prsnt_ocr_rdng AS BIGINT) > CAST(r.prsnt_rdng AS BIGINT) THEN 1 END) AS greater,
                COUNT(CASE WHEN r.prsnt_ocr_rdng ~ '^\d+$' AND r.prsnt_rdng ~ '^\d+$' AND CAST(r.prsnt_ocr_rdng AS BIGINT) < CAST(r.prsnt_rdng AS BIGINT) THEN 1 END) AS lesser
            FROM
                readingmaster r
            LEFT JOIN
                meterreaderregistration m ON m."mrId" = r.mr_id
            {clause} and r.{groupby}!=''
            GROUP BY
                r.{groupby}, r.mr_id, m."mrName", m."mrPhone"
            order by r.mr_id asc
        """

    lmquery = f"""SELECT {groupby}, r.mr_id, count(r.rdng_ocr_status='Passed' or null), count(r.prsnt_mtr_status='Ok' or null) FROM readingmaster r LEFT JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month','{(dates+'-01') if(dates) else date.today()}'::date - interval '1' month)
                and reading_date_db < date_trunc('month', '{(dates+'-01') if(dates) else date.today()}'::date ) {clause1} group by r.mr_id, {groupby}
            """
    
    print(query)
    cursor.execute(query)
    results = cursor.fetchall()
    cursorn.execute(lmquery)
    lmresults = cursorn.fetchall()

    lmaccuracy = {}
    for i in lmresults:
        passed = i[2]
        ok = i[3]
        accuracy = math.floor(((passed / ok) if ok else 0) * 100)
        lmaccuracy[i[1]] = accuracy

    end = time.time()
    print("total", end-start)
    count = 0
    try:
        for row in results:
            ocrreadingpercent = math.floor(
                (((row[8] / row[7]) if row[7] else 0) * 100)
            )

            # add to dictionary
            newdict["location"] = str(row[0])
            newdict["mrid"] =  row[1]
            newdict["name"] = row[2]
            newdict["mobile"] = row[3]
            newdict["totalReadings"] = row[4]
            newdict["DoorLocked"] =  row[5]
            newdict["MeterDefective"] = row[6]
            newdict["OK"] =  row[7]
            newdict["OCRwithoutExcep"] = row[8]
            newdict["OCRwithException"] = row[9]
            newdict["ocr_greater"] = row[10]
            newdict["ocr_lesser"] = row[11]
            newdict["OCRReadingspercent"] = ocrreadingpercent
            if row[1] in lmaccuracy:
                newdict["lastmonth"] = lmaccuracy[row[1]]
                newdict["incrdectrAccuracy"] = str(
                    ocrreadingpercent - lmaccuracy[row[1]]
                )
            else:
                newdict["lastmonth"] = ""
                newdict["incrdectrAccuracy"] = ""

            count = count + 1
            # add to list
            newdata = listfun(newdict)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000
        result_page = paginator.paginate_queryset(newdata, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])

# miter report section wise - 3rd table -updated
@api_view(['GET', 'POST'])
def metereportsectionwise(request):
    pagesize = request.query_params.get('pagesize', None)  # name of month 
    paginator = PageNumberPagination()
    groupby = request.data.get('groupby', None)
    # orderby=request.query_params.get('orderby',None)
    dates = request.data.get('month', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # category values
    locationName = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)  # name of categories

    cursor = connection.cursor()
    cursor1 = connection.cursor()
    new = []
    def listfun(dict):
        new.append(dict.copy())
        return new
    newdict = {}
    clause = 'WHERE '
    clause += f"extract(month from reading_date_db) = '{dates.split('-')[1]}' AND extract(year from reading_date_db) = '{dates.split('-')[0]}' " if (
        dates) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f" AND bl_agnc_name in ('Fluent Grid','Fluentgrid') "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') "
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass

    clause+=str1
    clause += f"AND {locationWise} ='{locationName}'" if (locationName) else ''
    clause +=" AND prsnt_rdng_ocr_excep != 'No Exception Found'"


    query = (f'''
            select {groupby}, m.ofc_zone, m.ofc_circle, m.ofc_division, m.ofc_subdivision, r.section, r."mrPhone", m.mr_id, (m.abnormality), (m.prsnt_rdng_ocr_excep), m.cons_ac_no, m.cons_name, count(m.prsnt_rdng_ocr_excep)
            from  readingmaster m LEFT JOIN meterreaderregistration r  ON  m.mr_id=r."mrId" {clause} and {groupby}!=''  group by {groupby}, m.prsnt_rdng_ocr_excep, m.ofc_zone, m.ofc_circle, m.ofc_division, m.ofc_subdivision, r.section, r."mrPhone", m.mr_id, m.abnormality,  m.cons_ac_no, m.cons_name order by (m.prsnt_rdng_ocr_excep) DESC 
        ''')

    cursor.execute(query)
    results = cursor.fetchall()

    queryforexception = (
        f''' SELECT count(m.prsnt_rdng_ocr_excep!='No Exception Found') from readingmaster m WHERE m.rdng_ocr_status='Failed' and  EXTRACT(MONTH FROM m.reading_date_db)={(dates.split('-')[1]) if(dates) else (date.today().month)} and EXTRACT(YEAR FROM m.reading_date_db)={(dates.split('-')[0]) if(dates) else (date.today().year)} ''')
    cursor1.execute(queryforexception)
    res = cursor1.fetchall()
    totalcounts = []
    for row in res:
        totalcounts.append(row[0])
    res = dictfetchall(cursor1)
    print(query)
    count = 0
    try:
        for row in results:
            # add to dictionary
            newdict['zone'] = row[1]
            newdict['circle'] = row[2]
            newdict['division'] = row[3]
            newdict['subdivision'] = row[4]
            newdict['section'] = str(row[5].split(' ')[0])
            newdict['mrmobilenumber'] = row[6]
            newdict['mrid'] = row[7]
            newdict['abnormalities'] = row[8]
            newdict['exception'] = row[9]
            newdict['consumerid'] = row[10]
            newdict['cons_name'] = row[11]
            newdict['totalexception'] = totalcounts[0]

            count = count + 1
            # totalcounts.append(count)
            # add to list
            newdata = listfun(newdict)

        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        result_page = paginator.paginate_queryset(newdata, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# Month wise OCR Accuracy -4th table
@api_view(['POST'])
def monthwiseocraccuracy(request):
    pagesize = request.query_params.get('pagesize', None)
    paginator = PageNumberPagination()
    paginator.page_size = 10
    year = request.data.get('year', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)  # category values
    cursor = connection.cursor()

    clause = 'WHERE '
    clause += f" extract(year from reading_date_db) = '{year}' " if (
        year) else f" extract(year from reading_date_db) = '{date.today().year}' "
    
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f" AND bl_agnc_name in ('Fluent Grid','Fluentgrid') "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') "
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    clause+=str1

    clause += f"AND {locationWise} ='{locationName}' " if (locationName) else ''
    year1=year if (year) else date.today().year
    query = (f'''
        WITH monthly_counts AS (
        SELECT {groupby} AS location,
        DATE_TRUNC('month', r.reading_date_db) AS month,
        COUNT(*) AS total_meters,
        COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS Ok,
        COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS Passed
        FROM readingmaster r LEFT JOIN meterreaderregistration m  ON r.mr_id= m."mrId"
        {clause}
        GROUP BY location, month
        ),
        monthly_percentages AS (
        SELECT location,
        month, CASE WHEN Ok = 0 THEN 0
        ELSE ROUND(Passed::NUMERIC / OK::NUMERIC  * 100, 2) END  AS ok_percentage
        FROM monthly_counts
        )
        SELECT location,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-01-01') AS jan ,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-02-01') AS feb,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-03-01') AS mar,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-04-01') AS apr,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-05-01') AS may,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-06-01') AS jun,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-07-01') AS jul,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-08-01') AS aug,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-09-01') AS sep,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-10-01') AS oct,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-11-01') AS nov,
        MAX(ok_percentage) FILTER (WHERE month = '{year1}-12-01') AS dec

        FROM monthly_percentages where location!=''
        GROUP BY location;
            ''')
    cursor.execute(query)
    print("query, ", query, "object", object)

    try:
        person_object=dictfetchall(cursor)
        print("person_object", person_object)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 15000
        result_page = paginator.paginate_queryset(person_object,request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# Month wise OCR Accuracy -MR - 5th Table
@api_view(['POST'])
def mrmonthwiseocraccuracy(request):
    pagesize = request.query_params.get('pagesize', None)
    paginator = PageNumberPagination()
    paginator.page_size = 10
    year = request.data.get('year', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    dates = request.data.get('dates', None)  # category values
    agency = request.data.get('agency', None)  # category values

    try:
        cursor = connection.cursor()
        clause = ''
        clause = 'WHERE '
        clause += f" extract(year from reading_date_db) = '{year}' " if (
            year) else f" extract(year from reading_date_db) = '{date.today().year}' "
        str1=''
        if agency in  ('Fluent Grid','Fluentgrid'):
            str1 += f" AND bl_agnc_name in ('Fluent Grid','Fluentgrid') "
        elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
            str1 += f"AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') "
        elif agency:
            str1 += f"AND bl_agnc_name='{agency}'"
        else:
            pass
        clause +=str1
        # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ''
        clause += f"AND {locationWise} ='{locationName}'" if (locationName) else ''
        year=year if (year) else date.today().year
        query = (f'''
        WITH monthly_counts AS (
            SELECT {groupby} AS location, r.mr_id as mrid, m."mrName" as name, m."mrPhone" as number,
            DATE_TRUNC('month', reading_date_db) AS month,
            
            COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS Ok,
            COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS Passed
            FROM readingmaster r LEFT JOIN meterreaderregistration m  ON r.mr_id= m."mrId"
            {clause}
            GROUP BY location, mrid, month,name,number
            ),
            monthly_percentages AS (
            SELECT location,mrid,name,number,
            month, CASE WHEN Ok = 0 THEN 0 
            ELSE ROUND(Passed::NUMERIC / OK::NUMERIC  * 100, 2) END AS ok_percentage
            FROM monthly_counts
            )
            SELECT location, mrid, name, number,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-01-01') AS jan,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-02-01') AS feb,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-03-01') AS mar,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-04-01') AS apr,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-05-01') AS may,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-06-01') AS jun,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-07-01') AS jul,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-08-01') AS aug,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-09-01') AS sep,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-10-01') AS oct,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-11-01') AS nov,
            MAX(ok_percentage) FILTER (WHERE month = '{year}-12-01') AS dec

            FROM monthly_percentages where location!=''
            GROUP BY location,mrid,name,number;
                ''')
        cursor.execute(query)
        
        # results = cursor.fetchall()
        # count = 0
        # location = {}
        person_object=dictfetchall(cursor)
        print("person_object",query)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 15000
        result_page = paginator.paginate_queryset(person_object,request)
        return paginator.get_paginated_response(result_page)

    except:
        return Response([])


@api_view(['POST'])
def newsection(request):
    data = []
    section = Consumers.objects.filter(
        ofc_section=request.data['ofc_section']).values_list('mr_unit').distinct()
    for row in section:
        data.append(row)
        print(row)
    return Response(data)


@api_view(['POST'])
def get_meter_status(request):
    data = []
    meterstatus = Consumers.objects.filter(
        prsnt_mtr_status=request.data['prsnt_mtr_status']).values_list('abnormality').distinct()
    for row in meterstatus:
        data.append(row)
        print(row)

    return Response(data)


@api_view(['POST'])
def get_exception(request):
    data = []
    exception = Consumers.objects.filter(
        prsnt_rdng_ocr_excep=request.data['prsnt_rdng_ocr_excep']).values_list('ofc_section').distinct()

    for row in exception:
        data.append(row)
        print(row)
    return Response(data)

################################################################################

# List of Consumers Billed - TABLE 6
@api_view(['POST'])
def listofconsumersbilled(request):
    pagesize = request.query_params.get('pagesize', None)
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    groupby = request.data.get('groupby', None)
    month = request.data.get('month', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()

    clause1 = 'WHERE '
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    # clause1 += f"bl_agnc_name ='{agency}' and " if (agency) else ''
    clause1 +=str1
    clause1 += f"{locationwise} ='{locationname}' and " if (
        locationname) else ''

    clause1 += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    # clause1 += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]} " if (
    #     month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    print("clas1", clause1)


    query = f'''select {groupby}, r.cons_ac_no, r.cons_name, 
            r.mr_id, m."mrName", r.prsnt_mtr_status,  r.abnormality, r.rdng_img, r.prsnt_rdng_ocr_excep
            from readingmaster r  JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause1}  and {groupby}!='' 
         '''

    cursor.execute(query)
    res = cursor.fetchall()
    count = 0
    newdata = []
    try:
        print("query0--000")
        for row in res:

            newdict = {}
            newdict['location'] = row[0]
            newdict['consacno'] = row[1]
            newdict['consname'] = row[2]
            newdict['mrid'] = row[3]
            newdict['mrname'] = row[4]
            newdict['meterstatus'] = row[5]
            newdict['abnormality'] = row[6]
            newdict['exception'] = row[8]
            if pagesize is not None:
                newdict['meterimg'] = row[7]

            count = count + 1
            newdata.append(newdict)

        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 25000

        result_page = paginator.paginate_queryset(newdata, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# List of Consumers Billed on OK Status - 7
@api_view(['POST'])
def listofconsumersbillok(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    groupby = request.data.get('groupby')
    pagesize = request.query_params.get('pagesize', None)
    month = request.data.get('month', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new

    clause = 'WHERE '
    # filter = f"bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause += str1
    filter = f"{locationwise} ='{locationname}' and " if (locationname) else ''
    clause += filter
    # clause += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
    #     month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = f''' select {groupby} as location,  r.cons_ac_no as consacno,  r.cons_name as consname, 
            r.mr_id as mrid,  m."mrName" as mrname,  (r.prsnt_mtr_status) as meterstatus,  r.abnormality as abnormality, r.rdng_img as meterimg,  r.prsnt_rdng_ocr_excep as exception
            from readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause}  and {groupby}!='' 
            order by r.prsnt_mtr_status='Ok' DESC
            '''
    # print("query",query)
    cursor.execute(query)
    result = cursor.fetchall()
    newdict = {}
    count = 0
    # resu = dictfetchall(cursor)
    try:

        for row in result:
            newdict['location'] = row[0]
            newdict['consacno'] = row[1]
            newdict['consname'] = row[2]
            newdict['mrid'] = row[3]
            newdict['mrname'] = row[4]
            newdict['meterstatus'] = row[5]
            newdict['abnormality'] = row[6]
            newdict['exception'] = row[8]
            if pagesize is not None:
                newdict['meterimg'] = row[7]

            count += 1

            newdata = addlist(newdict)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 25000
        result_page = paginator.paginate_queryset(newdata, request)
        # result_page = paginator.paginate_queryset(resu, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# List of Consumers Billed on Vision-OCR OK Status - 8
@api_view(['POST', 'GET'])
def consmbillocrwithok(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    month = request.data.get('month', None)
    groupby = request.data.get('groupby')
    pagesize = request.query_params.get('pagesize', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    # paginator.page_size = pagesize
    cursor = connection.cursor()

    clause = 'WHERE '
    # filter = f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause += str1
    filter = f"{locationwise} ='{locationname}' and " if (locationname) else ''
    clause += filter
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    cond = "" if pagesize is None else "r.rdng_img as meterimg,"
    query = (f''' SELECT {groupby} as location, r.cons_ac_no as consacno, r.cons_name as consname, 
            r.mr_id as mrid,  m."mrName" as mrname, (r.rdng_ocr_status) as meterstatus,  r.abnormality as abnormality, {cond}  r.prsnt_rdng_ocr_excep as exception
            from readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and r.rdng_ocr_status='Passed' and {groupby}!='' order by r.rdng_ocr_status='Passed' DESC 
            ''')
    cursor.execute(query)
    # res = cursor.fetchall()
    try:
        result = dictfetchall(cursor)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 25000
        respage = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(respage)
    except:
        return Response([])

# List of Consumers Billed on Vision-OCR With Exception Status - 9
@api_view(['GET', 'POST'])
def consmbillocrwithexcept(request):  # sourcery skip: avoid-builtin-shadow
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    groupby = request.data.get('groupby')
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize', None)
    month = request.data.get('month', None)
    agency = request.data.get('agency', None)
    cursor = connection.cursor()

    clause = 'WHERE '
    # filter = f"bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause += str1
    filter = f"{locationwise} ='{locationname}' and " if (locationname) else ''
    clause += filter
    # clause += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
    #     month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = f''' SELECT {groupby} as location, r.cons_ac_no as consacno, r.cons_name as consname, 
            r.mr_id as mrid,  m."mrName" as mrname, (r.rdng_ocr_status) as meterstatus,  r.abnormality as abnormality, r.prsnt_rdng_ocr_excep as exception
            from readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and  r.rdng_ocr_status='Failed' and {groupby}!=''  group by {groupby}, r.cons_ac_no, r.cons_name,r.mr_id, m."mrName",  r.rdng_ocr_status ,  r.abnormality , r.rdng_img ,  r.prsnt_rdng_ocr_excep 
            '''
    cursor.execute(query)
    # res = cursor.fetchall()
    try:
        result = dictfetchall(cursor)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 25000
        respage = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(respage)
    except:
        return Response([])


# Summary of Exceptions - 10
@api_view(['GET', 'POST'])
def exceptionsummary(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    groupby = request.data.get('groupby', None)
    pagesize = request.query_params.get('pagesize', None)
    paginator = PageNumberPagination()
    month = request.data.get('month', None)
    agency = request.data.get('agency', None)
    cursor = connection.cursor()
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new

    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = f''' SELECT {groupby} as location, count(r.id), count(r.prsnt_mtr_status='Door Locked' or null)as dl,  count(r.prsnt_mtr_status='Meter Defective' or null)as md, count(r.prsnt_mtr_status='Ok' or null)as ok, count(r.rdng_ocr_status='Passed' or null)as passed, count(r.rdng_ocr_status='Failed' or null)as failed
                from readingmaster r  LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and {groupby}!='' group by {groupby}
            '''
    cursor.execute(query)
    result = cursor.fetchall()
    print("result---->", result)
    newdict = {}
    count = 0
    try:
        for row in result:
            ocraccuracy = str(math.floor(
                ((row[5]/row[4])if row[4] else 0)*100))
            newdict['location'] = row[0]
            newdict['total'] = row[1]
            newdict['dl'] = row[2]
            newdict['md'] = row[3]
            newdict['ok'] = row[4]
            newdict['passed'] = row[5]
            newdict['failed'] = row[6]
            newdict['accuracy'] = ocraccuracy
            count += 1

            res = addlist(newdict)

        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 18000
        res_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("Exception", e)
        return Response([])


# List of Consumers with Defective Meters(MD) - 11
@api_view(['GET', 'POST'])
def listconsmwithmd(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    groupby = request.data.get('groupby')
    month = request.data.get('month', None)
    pagesize = request.query_params.get('pagesize', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()
    cursor1 = connection.cursor()
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new
    clause = 'WHERE '
    # str = f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause += str1
    str = f" {locationwise} ='{locationname}' and " if (locationname) else ''
    clause += str
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = (f''' SELECT {groupby} as location, r.cons_ac_no as consacno, r.cons_name as consname,
                  r.mr_id as mrid,  m."mrName" as mrname, r.rdng_img as meterimg
                  FROM readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and prsnt_mtr_status='Meter Defective' and {groupby}!=''  
            ''')
    cursor.execute(query)
    result = cursor.fetchall()
    querynew = (
        f'''
            SELECT 
                count(r.prsnt_mtr_status='Meter Defective' or null) as mdcount 
            from readingmaster r where EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1]) if(month) else (date.today().month)} AND extract(year from reading_date_db) = {(month.split('-')[0]) if(month) else (date.today().year)} ''')
    cursor1.execute(querynew)
    newdict = {}
    count = 0
    # total=[]
    try:
        resn = dictfetchall(cursor1)
        for row in result:
            newdict['location'] = row[0]
            newdict['consacno'] = row[1]
            newdict['consname'] = row[2]
            newdict['mrid'] = row[3]
            newdict['mrname'] = row[4]
            # newdict['countmd']=row[6]
            count += 1
            newdict['totalmd'] = resn[0]['mdcount']
            if pagesize is not None:
                newdict['meterimg'] = row[5]
            # print("count", count)

            res = addlist(newdict)
            if pagesize:
                paginator.page_size = pagesize
            else:
                paginator.page_size = 25000
        # print("total,", len(total))
        res_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(res_page)

    except:
        return Response([])

# List of Consumers with Door Lock (LK) - 12
@api_view(['GET', 'POST'])
def listconsmwithdl(request):
    locationwise = request.data.get('locationwise')
    locationname = request.data.get('locationname')
    groupby = request.data.get('groupby')
    month = request.data.get('month', None)
    pagesize = request.query_params.get('pagesize')
    paginator = PageNumberPagination()
    cursor = connection.cursor()
    cursor1 = connection.cursor()
    agency = request.data.get('agency', None)
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new

    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = (f''' SELECT {groupby} as location, r.cons_ac_no as consacno, r.cons_name as consname,
                  r.mr_id as mrid,  m."mrName" as mrname, r.rdng_img as meterimg
                  FROM readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and r.prsnt_mtr_status='Door Locked' and {groupby}!='' 
            ''')

    print("query", query)
    cursor.execute(query)
    result = cursor.fetchall()
    querynew = (
        f'''SELECT count(r.prsnt_mtr_status='Door Locked' or null) as dlcount from readingmaster r where EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1]) if(month) else (date.today().month)} AND extract(year from reading_date_db) = {(month.split('-')[0]) if(month) else (date.today().year)} ''')
    cursor1.execute(querynew)
    # resnew=cursor.fetchall()
    newdict = {}
    count = 0
    try:
        resn = dictfetchall(cursor1)
        for row in result:
            newdict['location'] = row[0]
            newdict['consacno'] = row[1]
            newdict['consname'] = row[2]
            newdict['mrid'] = row[3]
            newdict['mrname'] = row[4]
            if pagesize is not None:
                newdict['meterimg'] = row[5]
            # newdict['countdl']=row[6]

            count += 1
            newdict['totaldl'] = resn[0]['dlcount']
            res = addlist(newdict)

        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 25000
        
        res_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(res_page)
        # return Response(res_page and resn)

    except:
        return Response([])

# List of Abnormalities Report - 13
@api_view(['POST', 'GET'])
def abnormalitieslist(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    month = request.data.get('month', None)
    groupby = request.data.get('groupby', None)
    pagesize = request.query_params.get('pagesize', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new
    newdict = {}
    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = f''' select DISTINCT {groupby} as location,
                count(r.abnormality='Everything is Ok' or null) as "1",
                count(r.abnormality='Dirty Meter' or null) as "2",
                count(r.abnormality='No Meter' or null) as "3",
                count(r.abnormality='Meter Broken/Seal' or null) as "4",
                count(r.abnormality='Meter Shifting to Doorbell Loc' or null) as "5",
                count(r.abnormality='Mtr. Digit Mismatch' or null) as "6",
                count(r.abnormality='Meter On Height' or null) as "7",
                count(r.abnormality='Suspected Faulty' or null) as "8",
                count(r.abnormality='Consumer Not Traceable' or null) as "9",
                count(r.abnormality='Reading Refused by Consumer' or null) as "10",
                count(r.abnormality='Theft' or null) as "11",
                count(r.abnormality='Electro-Mechanical Meter' or null) as "12",
                count(r.abnormality='Meter Bypass' or null) as "13",
                count(r.abnormality='Category Mismatch' or null) as "14",
                count(r.abnormality='Meter Number Mismatch' or null) as "15"
                from readingmaster r LEFT JOIN meterreaderregistration m ON r.mr_id=m."mrId" {clause} and {groupby}!='' group by  {groupby}
            '''
    cursor.execute(query)
    result = cursor.fetchall()
    count = 0
    newdict = {}
    try:
        # res = dictfetchall(cursor)
        for row in result:
            newdict["location"] = row[0]
            newdict["Abnormality1"] = row[1]
            newdict["Abnormality2"] = row[2]
            newdict["Abnormality3"] = row[3]
            newdict["Abnormality4"] = row[4]
            newdict["Abnormalit5"] = row[5]
            newdict["Abnormality6"] = row[6]
            newdict["Abnormality7"] = row[7]
            newdict["Abnormality8"] = row[8]
            newdict["Abnormality9"] = row[9]
            newdict["Abnormality10"] = row[10]
            newdict["Abnormality11"] = row[11]
            newdict["Abnormality12"] = row[12]
            newdict["Abnormality13"] = row[13]
            newdict["Abnormality14"] = row[14]
            newdict["Abnormality15"] = row[15]
            count = count+1
            res = addlist(newdict)

            if pagesize:
                paginator.page_size = pagesize
            else:
                paginator.page_size = 17000
        res_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print('Exception_Error', str(e))
        return Response([])


# Meter Reader Wise Performance Report - 14
@api_view(['GET', 'POST'])
def mrwiseperformancereport(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    month = request.data.get('month', None)
    groupby = request.data.get('groupby', None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize')
    current_month = date.today().month
    last_month = ""
    if current_month == 1:
        last_month = 12
    else:
        last_month = int(date.today().month-1)
    cursor = connection.cursor()
    clause = f"WHERE "
    # clause += f" agency ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"agency in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"agency in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"agency='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (locationname) else ''
    # clause += f" EXTRACT(MONTH FROM m.month)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM m.month)={last_month} "
    clause += f"extract(month from m.month) = '{month.split('-')[1]}' AND extract(year from m.month) = '{month.split('-')[0]}' " if (month) else f"extract(month from m.month) = '{date.today().month}' AND extract(year from m.month) = '{date.today().year}' "
    print("clas1", clause)

    query = f''' 
            SELECT {groupby} as location, m.mrid, sum(total) as total, 
            sum(m.md) as md,
            sum(m.dl) as dl,
            sum(m.ok) as ok,
            sum(m.passed) as passed,
            sum(m.failed) as failed,
            sum(m.passedper) as ocr_pass_percent
            FROM mr_wise_performance_report m  {clause} and {groupby}!=''
            GROUP by {groupby},m.mr_unit,m.total,m.mrid,m.md,m.dl,m.ok,m.passed,m.failed
            order by m.mrid asc
        '''
    cursor.execute(query)
    # res=cursor.fetchall()
    try:
        result = dictfetchall(cursor)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 30000

        res_page = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("Exception_", e)
        return Response([])


@api_view(['GET'])
def filter_discom(request):
    newlist = []
    discom = (Consumers.objects.values_list('ofc_discom').distinct())
    for row in discom:
        print(row[0])
        newlist.append(row[0])
        # print(newlist)
    return Response(newlist)


@api_view(['POST'])
def filter_agency(request):
    newlist = []
    agency = Consumers.objects.filter(
        ofc_discom=request.data['ofc_discom']).values_list('bl_agnc_name').distinct()
    for row in agency:
        newlist.append(row[0])
        # print(newlist)
    return Response(newlist)


@api_view(['GET', 'POST'])
def filter_mrid(request):
    newlist = []
    agency = Consumers.objects.filter(
        bl_agnc_name=request.data['bl_agnc_name']).values_list('mr_id').distinct()
    for row in agency:
        newlist.append(row[0])
        # print(newlist)
    return Response(newlist)

# Section for Abnormality


@api_view(['GET', 'POST'])
def sectionabnorm(request):
    newlist = []
    section = Consumers.objects.filter(
        ofc_section=request.data['ofc_section']).values_list('abnormality').distinct()
    for i in section:
        newlist.append(i[0])
        # print(newlist)
    return Response(newlist)

# Section for mr_unit
@api_view(['GET', 'POST'])
def mrunitsection(request):
    newlist = []
    section = Consumers.objects.filter(
        mr_unit=request.data['mr_unit']).values_list('ofc_section').distinct()
    for i in section:
        newlist.append(i[0])
        # print(newlist)
    return Response(newlist)

# Section for mr_unit
@api_view(['GET', 'POST'])
def subdivision(request):
    newlist = []
    subdiv = Consumers.objects.filter(
        ofc_subdivision=request.data['ofc_subdivision']).values_list('mr_unit').distinct()
    for i in subdiv:
        newlist.append(i[0])
        # print(newlist)
    return Response(newlist)


@api_view(['GET', 'POST'])
def newsectionunit(request):
    newlist = []
    sec = Consumers.objects.filter(
        ofc_section=request.data['ofc_section']).values_list('mr_unit').distinct()
    for i in sec:
        newlist.append(i[0])
        # print(newlist)
    return Response(newlist)


@api_view(['GET', 'POST'])
def get_new_agency(request):
    newlist = []
    # agency = (Consumers.objects.values_list('bl_agnc_name').distinct())
    agency = (Office.objects.values_list('agency').distinct())
    for row in agency:
        print(row[0])
        if row[0] not in ('BCITS PVT LTD-IPDS','DATA INGENIOUS', 'Fluent Grid', 'FG', 'Quess Corp(Ikya Rural)'):
            newlist.append(row[0])
        # print(newlist)
    return Response(newlist)


# Performance Report - Agency wise - 15
@api_view(['POST'])
def agencyperformancereport(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    month = request.data.get('month', None)
    groupby = request.data.get('groupby')
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize', None)
    cursor = connection.cursor()

    clause = 'WHERE '
    clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    # str1=''
    # if agency in  ('Fluent Grid','Fluentgrid'):
    #     str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    # elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
    #     str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    # elif agency:
    #     str1 += f"bl_agnc_name='{agency}' AND "
    # else:
    #     pass
    # clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = (f'''SELECT 
            CASE
                WHEN r.bl_agnc_name IN ('DATA INGENIOUS', 'Data Ingenious') THEN 'Data Ingenious'
                WHEN r.bl_agnc_name IN ('Fluent Grid','Fluentgrid') THEN 'Fluentgrid'
                ELSE r.bl_agnc_name
            END AS agencyname,
            count(r.mr_id) as total_count, count(distinct r.mr_id) as countmr,
            count(r.prsnt_mtr_status='Meter Defective' or null)as md,
            count(r.prsnt_mtr_status='Door Locked' or null)as dl,
            count(r.prsnt_mtr_status='Ok' or null)as ok,
            count(r.rdng_ocr_status='Passed' or null)as passed,
            count(r.rdng_ocr_status='Failed' or null)as failed,
            CASE WHEN count(prsnt_mtr_status='Ok' or NULL) = 0 THEN 0
            ELSE ROUND((cast(count(rdng_ocr_status='Passed' or null) as float)
            /cast(count(prsnt_mtr_status='Ok' or null) as float) * 100)::numeric, 2)  
            END  as ocr_pass_percent
            from readingmaster r  {clause} and r.bl_agnc_name!='BCITS' and r.{groupby}!='' group by agencyname order by ocr_pass_percent asc
            ''')

    print(query)
    cursor.execute(query)
    # res=cursor.fetchall()
    try:
        result = dictfetchall(cursor)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        res_page = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("Exception_", e)
        return Response([])

# Performance reports Location wise -16
@api_view(['GET', 'POST'])
def locwiseperformancereport(request):
    locationwise = request.data.get('locationwise')
    locationname = request.data.get('locationname')
    month = request.data.get('month', None)
    groupby = request.data.get('groupby')
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize')
    cursor = connection.cursor()

    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={(month.split('-')[1])}" if (
    #     month) else f" EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause)

    query = (f''' 
            SELECT DISTINCT {groupby} as location, count(r.mr_id),
            count(r.prsnt_mtr_status='Meter Defective' or null)as md,
            count(r.prsnt_mtr_status='Door Locked' or null)as dl,
            count(r.prsnt_mtr_status='Ok' or null)as ok,
            count(r.rdng_ocr_status='Passed' or null)as passed,
            count(r.rdng_ocr_status='Failed' or null)as failed,
            CASE WHEN count(prsnt_mtr_status='Ok' or NULL) = 0 THEN 0
            ELSE ROUND((cast(count(rdng_ocr_status='Passed' or null) as float)
            /cast(count(prsnt_mtr_status='Ok' or null) as float) * 100)::numeric, 2)
            END as ocr_pass_percent
            FROM readingmaster r left JOIN meterreaderregistration m ON r.mr_id = m."mrId" {clause} and {groupby}!=''
            GROUP BY {groupby}
        ''')
    cursor.execute(query)
    # res=cursor.fetchall()
    try:
        result = dictfetchall(cursor)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        res_page = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("Exception_", e)
        return Response([])


# Performance Report(Vision-OCR) - Month Wise - 17
@api_view(['POST'])
def monthwiseperformance(request):
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize', None)
    year = request.data.get('year', None)  # name of month
    locationwise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    agency = request.data.get('agency', None)
    locationname = request.data.get('locationname', None)  # category values 
    # print("locationName >>>>>>",locationName)
    cursor = connection.cursor()

    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    clause += f" EXTRACT(YEAR FROM r.reading_date_db)={year}" if (
        year) else f" EXTRACT(YEAR FROM r.reading_date_db)={date.today().year}"
    print("clause-----------", clause)

    import time
    start = time.time() 
    query = (f''' SELECT {groupby} , EXTRACT(MONTH FROM reading_date_db) AS month, COUNT(r.prsnt_mtr_status='Ok' or null), count(r.rdng_ocr_status='Passed' or null)
            FROM readingmaster r {clause}  and {groupby}!=''
            GROUP BY  {groupby}, month
            ''')
    print ("query, ", query)
    cursor.execute(query)
    results = cursor.fetchall()
    print(time.time()-start)
    location = {}
    count = 0
    try:
        for i in results:
            ocraccuracy = (((i[3]/i[2])if i[2] else 0)*100)
            ocraccuracy = "%.2f" % ocraccuracy
            if i[0] not in location:
                location[i[0]] = {}
            if i[1] == 1:
                location[i[0]].update({'jan': str(ocraccuracy)})
            elif i[1] == 2:
                location[i[0]].update({'feb': str(ocraccuracy)})
            elif i[1] == 3:
                location[i[0]].update({'mar': str(ocraccuracy)})
            elif i[1] == 4:
                location[i[0]].update({'april': str(ocraccuracy)})
            elif i[1] == 5:
                location[i[0]].update({'may': str(ocraccuracy)})
            elif i[1] == 6:
                location[i[0]].update({'june': str(ocraccuracy)})
            elif i[1] == 7:
                location[i[0]].update({'july': str(ocraccuracy)})

            elif i[1] == 8:
                location[i[0]].update({'aug': str(ocraccuracy)})

            elif i[1] == 9:
                location[i[0]].update({'sep': str(ocraccuracy)})

            elif i[1] == 10:
                location[i[0]].update({'oct': str(ocraccuracy)})

            elif i[1] == 11:
                location[i[0]].update({'nov': str(ocraccuracy)})
            elif i[1] == 12:
                location[i[0]].update({'dec': str(ocraccuracy)})

        res = []
        for key, value in location.items():
            k = {}
            k["location"] = key
            k.update(value)
            res.append(k)

            count += 1
        print(time.time()-start)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        result_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# Month wise Comparision Report -Abnormalities - 18 -update && Exception - 19 -update
@api_view(['POST'])
def mothwisecomreports(request):
    pagesize = request.query_params.get("pagesize", None)
    condition = request.data.get("condition")
    year = request.data.get("year", None)
    groupby = request.data.get("groupby")
    locationname = request.data.get("locationname", None)
    locationwise = request.data.get("locationwise", None)
    agency = request.data.get('agency', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()

    clause = 'WHERE '
    # clause += f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause+=str1
    clause += f" {locationwise} ='{locationname}' and " if (
        locationname) else ''
    clause += f" EXTRACT(YEAR FROM r.reading_date_db)={(year.split('-')[0])}" if (
        year) else f" EXTRACT(YEAR FROM r.reading_date_db)={date.today().year}"
    print("clas1", clause)

    location = {}
    month = date.today().month
    print("clause------------>", clause)
    try:

        query = f'''select {groupby} as location, ROUND((cast(count({condition}) as float) / cast(count(r.mr_id) as float) * 100)::numeric, 2) as percentage, EXTRACT(MONTH from r.reading_date_db)
                            from readingmaster r left JOIN meterreaderregistration m ON r.mr_id = m."mrId" {clause} and EXTRACT(month from reading_date_db)>=1 and EXTRACT(month from reading_date_db)<={month} and {groupby}!='' group by {groupby}, reading_date_db
                        '''

        cursor.execute(query)
        res = cursor.fetchall()
        # print(res)

        print(query)

        for row in res:
            if row[0] not in location:
                location[row[0]] = {}
                location[row[0]].update({chr(64+int(row[2])): row[1]})
            else:
                location[row[0]].update({chr(64+int(row[2])): row[1]})

        res = []
        # print(location)

        for key, value in location.items():
            if key != "":
                k = {}
                k["location"] = key
                k.update(value)
                res.append(k)
                # count += 1

        paginator.page_size = pagesize or 17000

        res_page = paginator.paginate_queryset(res, request)
        return paginator.get_paginated_response(res_page)
    except Exception as e:
        print("Exception", e)
        return Response([])

# Vision- OCR - Failed in Previous Months but Successful currently - 20
@api_view(['POST'])
def visionocrfailedpremon(request):
    pagesize = request.query_params.get('pagesize', None)  # name of month 
    paginator = PageNumberPagination()
    print("paginator", paginator)
    month = request.data.get('month', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)  # name of agency
    cursor = connection.cursor()
    cursorn = connection.cursor()

    clause1 = 'WHERE '
    clause2 = 'AND '
    # filter = f"bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause1 += str1
    clause2 += str1
    filter = f"{locationWise} ='{locationName}' and " if (locationName) else ''
    clause1 += filter
    clause2 += filter
    # clause1 += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
    #     month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause1 += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "

    query = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
            from readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id {clause1} and r.rdng_ocr_status='Passed' and {groupby}!=''   
            '''

    lmquery = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
            FROM readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month', current_date - interval '1' month)
            and reading_date_db < date_trunc('month', current_date) {clause2} r.rdng_ocr_status='Failed' 
            '''

    cursor.execute(query)
    results = cursor.fetchall()
    cursorn.execute(lmquery)
    lmresults = cursorn.fetchall()
    lmaccuracy = {}
    location = []
    count = 0

    print("clas1", query)
    print("clas2", lmquery)
    
    try:

        for i in results:
            if (i[3] not in lmaccuracy):
                lmaccuracy[i[3]] = {
                    "location": i[0],
                    "mrid": i[1],
                    "consname": i[2],
                    "consaccno": i[3],
                    "meterimg": i[4],
                }

        for i in lmresults:
            if (i[3] in lmaccuracy):
                location.append(lmaccuracy[i[3]])

            count += 1
            # newdata = listfun(newdict)
        print("lmresults", location)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        result_page = paginator.paginate_queryset(location, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# Vision- OCR - Successful in Previous Months but Failed currently - 21
@api_view(['POST'])
def visionocrpassedpremon(request):
    pagesize = request.query_params.get('pagesize', None)  # name of month 
    paginator = PageNumberPagination()
    print("paginator", paginator)
    month = request.data.get('month', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)
    print(">>>>>>", locationName)
    cursor = connection.cursor()
    cursorn = connection.cursor()

    clause = f"WHERE "
    # clause += f" EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1] if(month) else date.today().month} "
    clause += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    clause += f" AND {locationWise}='{locationName}' " if (
        locationName) else ""
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ""
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"AND bl_agnc_name in ('Fluent Grid','Fluentgrid')"
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f" AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious')"
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    clause+=str1
    print("clause", clause)
    lmquery = ''

    query = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
            from readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id {clause} and r.rdng_ocr_status='Failed' and {groupby}!=''  group by {groupby}, r.mr_id, r.cons_name, r.rdng_img, r.cons_ac_no
            '''
    if locationWise and locationName is not None:
        lmquery = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
                FROM readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month', current_date - interval '1' month)
                and reading_date_db < date_trunc('month', current_date) AND  {locationWise}='{locationName}' AND r.rdng_ocr_status='Passed' group by {groupby}, r.mr_id, r.cons_name, r.rdng_img, r.cons_ac_no
                '''
    else:
        lmquery = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
                FROM readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month', current_date - interval '1' month)
                and reading_date_db < date_trunc('month', current_date)  AND r.rdng_ocr_status='Passed' group by {groupby}, r.mr_id, r.cons_name, r.rdng_img, r.cons_ac_no
                '''

    cursor.execute(query)
    results = cursor.fetchall()
    cursorn.execute(lmquery)
    lmresults = cursorn.fetchall()
    lmaccuracy = {}
    location = []
    count = 0
    try:

        for i in results:
            if (i[3] not in lmaccuracy):
                lmaccuracy[i[3]] = {
                    "location": i[0],
                    "mrid": i[1],
                    "consname": i[2],
                    "consaccno": i[3],
                    "meterimg": i[4],
                }

        for i in lmresults:
            if (i[3] in lmaccuracy):
                location.append(lmaccuracy[i[3]])
            count += 1
            # newdata = listfun(newdict)
            if pagesize:
                paginator.page_size = pagesize
            else:
                paginator.page_size = 17000

        result_page = paginator.paginate_queryset(location, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])


# Defective Meter Aging Report - 22
@api_view(['GET', 'POST'])
def defectivemtraging(request):
    locationwise = request.data.get('locationwise', None)
    locationname = request.data.get('locationname', None)
    pagesize = request.query_params.get('pagesize', None)
    groupby = request.data.get('groupby', None)
    month = request.data.get('month', None)
    agency = request.data.get('agency', None)
    day1 = request.data.get('day1', None)
    day2 = request.data.get('day2', None)
    paginator = PageNumberPagination()
    cursor = connection.cursor()
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new

    clause = f"WHERE "
    clause += f" {locationwise}='{locationname}' " if locationname else ""
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ""
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"AND bl_agnc_name in ('Fluent Grid','Fluentgrid')"
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f" AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious')"
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    clause+=str1
    query = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg, r.prsnt_mtr_status='Meter Defective' as meterdefective, r.reading_date_db, (CURRENT_DATE - r.reading_date_db)
            from readingmaster r left JOIN meterreaderregistration m ON  m."mrId"=r.mr_id {clause} and {groupby}!='' and r.prsnt_mtr_status='Meter Defective' AND (CURRENT_DATE - r.reading_date_db) > {day1} AND (CURRENT_DATE - r.reading_date_db) < {day2}
        '''
    cursor.execute(query)
    print("query", query,"hjhj============",clause)
    res = cursor.fetchall()
    # print("ressssssssssssss", res)
    newdict = {}
    count = 0
    result = []
    try:
        for row in res:
            newdict["location"] = row[0]
            newdict["mrid"] = row[1]
            newdict["consname"] = row[2]
            newdict["consacno"] = row[3]
            newdict["meterimg"] = row[4]
            # newdict["defdays"]=row[7]
            days_input = row[7]
            monthss = days_input//30
            days = days_input-monthss*30
            newdict["defdays"] = (f"{monthss} Month, " f"{days} Days")
            count += 1
            result = addlist(newdict)
            # print (" results   ->", result)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 21000
        respage = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(respage)
    except Exception as e:
        print("Exception", e)
        return Response([])

# Door Lock Aging Report - 23
@api_view(['GET', 'POST'])
def dlmeteraging(request):
    locationwise = request.data.get('locationwise')
    locationname = request.data.get('locationname')
    pagesize = request.query_params.get('pagesize')
    agency = request.data.get('agency', None)
    groupby = request.data.get('groupby')
    day1 = request.data.get('day1')
    day2 = request.data.get('day2')

    paginator = PageNumberPagination()
    cursor = connection.cursor()
    query = ''
    params = ''
    new = []

    def addlist(dict):
        new.append(dict.copy())
        return new

    clause = f"WHERE "
    clause += f" {locationwise}='{locationname}' " if locationname else ""
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ""
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"AND bl_agnc_name in ('Fluent Grid','Fluentgrid')"
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f" AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious')"
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    clause+=str1

    query = f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg, r.prsnt_mtr_status as meterdefective, r.reading_date_db, (CURRENT_DATE - r.reading_date_db)
            from readingmaster r LEFT JOIN meterreaderregistration m ON m."mrId" = r.mr_id {clause} and {groupby}!='' and r.prsnt_mtr_status='Door Locked' AND (CURRENT_DATE - r.reading_date_db) > {day1} and (CURRENT_DATE - r.reading_date_db) < {day2} 
    '''

    cursor.execute(query, params)
    res = cursor.fetchall()
    print(query)
    newdict = {}
    count = 0
    try:
        for row in res:
            newdict["location"] = row[0]
            newdict["mrid"] = row[1]
            newdict["consname"] = row[2]
            newdict["consacno"] = row[3]
            newdict["meterimg"] = row[4]
            days_input = row[7]
            month = days_input//30
            days = days_input-month*30
            newdict["defdays"] = (f"{month} Month, " f"{days} Days")
            # newdict["defdays"]=row[7]
            count += 1
            result = addlist(newdict)
            if pagesize:
                paginator.page_size = pagesize
            else:
                paginator.page_size = 21000
        respage = paginator.paginate_queryset(result, request)
        return paginator.get_paginated_response(respage)
    except:
        return Response([])

####
# Vision- OCR - Defective in Previous Months but Everything is ok currently - 24
# @api_view(['POST'])
# def defectprevmonthandoknow(request):
#     paginator = PageNumberPagination()
#     pagesize = request.query_params.get('pagesize', None)  # name of month 
#     print("paginator", paginator)
#     month = request.data.get('month', None)  # name of month
#     locationWise = request.data.get('locationwise', None)  # name of categories
#     groupby = request.data.get('groupby', None)  # name of categories
#     locationName = request.data.get('locationname', None)  # category values
#     agency = request.data.get('agency', None)
#     print(">>>>>>", locationName)
#     cursor = connection.cursor()
#     cursorn = connection.cursor()

#     clause1 = 'WHERE '
#     clause2 = ''
#     filter = f" bl_agnc_name ='{agency}' and " if (agency) else ''
#     clause1 += filter
#     clause2 += filter
#     filter = f" {locationWise} ='{locationName}' and " if (
#         locationName) else ''
#     clause1 += filter
#     clause2 += filter
#     clause1 += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
#         month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
#     print("clas1", clause1)
#     print("clas2", clause2)

#     query = (f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
#             from readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id {clause1} AND r.prsnt_mtr_status !='Meter Defective' 
#             ''')
#     lmquery = (f'''SELECT {groupby} as location, r.mr_id as mrid, r.cons_name as consname, r.cons_ac_no as consacno, r.rdng_img as meterimg
#             FROM readingmaster r JOIN meterreaderregistration m ON m."mrId" = r.mr_id WHERE  reading_date_db >= date_trunc('month', current_date - interval '1' month)
#             and reading_date_db < date_trunc('month', current_date) AND  {clause2} r.prsnt_mtr_status ='Meter Defective'
#             ''')
    
#     cursor.execute(query)
#     results = cursor.fetchall()
#     cursorn.execute(lmquery)
#     lmresults = cursorn.fetchall()
#     lmaccuracy = {}
#     location = []
#     count = 0
#     try:

#         for i in results:
#             if (i[3] not in lmaccuracy):
#                 lmaccuracy[i[3]] = {
#                     "location": i[0],
#                     "mrid": i[1],
#                     "consname": i[2],
#                     "consaccno": i[3],
#                     "meterimg": i[4],
#                 }
        
#         print(lmaccuracy)
#         for i in lmresults:
#             if (i[3] in lmaccuracy):
#                 location.append(lmaccuracy[i[3]])
#             count += 1
#             # newdata = listfun(newdict)
#             if pagesize:
#                 paginator.page_size = pagesize
#             else:
#                 paginator.page_size = 17000

#         result_page = paginator.paginate_queryset(location, request)
#         return paginator.get_paginated_response(result_page)
#     except:
#         return Response([])

@api_view(['POST'])
def defectprevmonthandoknow(request):
    paginator = PageNumberPagination()
    pagesize = request.query_params.get('pagesize', None)  # name of month 
    print("paginator", paginator)
    month = request.data.get('month', None)  # name of month
    locationWise = request.data.get('locationwise', None)  # name of categories
    groupby = request.data.get('groupby', None)  # name of categories
    locationName = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)
    print(">>>>>>", locationName)
    cursor = connection.cursor()
    cursorn = connection.cursor()

    clause1 = 'WHERE '
    clause2 = ''
    # filter = f" bl_agnc_name ='{agency}' and " if (agency) else ''
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"bl_agnc_name in ('Fluent Grid','Fluentgrid') AND "
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f"bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious') AND "
    elif agency:
        str1 += f"bl_agnc_name='{agency}' AND "
    else:
        pass
    clause1 += str1
    clause2 += str1
    filter = f" {locationWise} ='{locationName}' and " if (
        locationName) else ''
    clause1 += filter
    clause2 += filter
    # clause1 += f"EXTRACT(MONTH FROM r.reading_date_db)={month.split('-')[1]}" if (
    #     month) else f"EXTRACT(MONTH FROM r.reading_date_db)={date.today().month}"
    clause1 += f"extract(month from reading_date_db) = '{month.split('-')[1]}' AND extract(year from reading_date_db) = '{month.split('-')[0]}' " if (month) else f"extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' "
    print("clas1", clause1)
    print("clas2", clause2)

    query = f'''
        SELECT 
            current.location,
            current.mrid,
            current.consname,
            current.consacno,
            current.meterimg
        FROM 
            (
                SELECT 
                    {groupby} AS location, 
                    r.mr_id AS mrid, 
                    r.cons_name AS consname, 
                    r.cons_ac_no AS consacno, 
                    r.rdng_img AS meterimg
                FROM 
                    readingmaster r 
                    JOIN meterreaderregistration m ON m."mrId" = r.mr_id 
                {clause1} AND r.prsnt_mtr_status != 'Meter Defective'
            ) AS current
        JOIN
            (
                SELECT 
                    r.cons_ac_no AS consacno
                FROM 
                    readingmaster r 
                    JOIN meterreaderregistration m ON m."mrId" = r.mr_id 
                WHERE 
                    r.reading_date_db >= date_trunc('month', current_date - interval '1' month)
                    AND r.reading_date_db < date_trunc('month', current_date) 
                    AND {clause2} r.prsnt_mtr_status = 'Meter Defective'
            ) AS past
        ON 
            current.consacno = past.consacno
        where current.location!=''
    '''

    print(query)
    
    cursor.execute(query)
    results = cursor.fetchall()
    location = []
    try:

        for i in results:
            location.append(
                {
                    "location": i[0],
                    "mrid": i[1],
                    "consname": i[2],
                    "consaccno": i[3],
                    "meterimg": i[4],
                })

        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        result_page = paginator.paginate_queryset(location, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])

# ## Vision- OCR - Ok in Previous Months but Failed currently - 25
@api_view(['POST'])
def okprevmonbutfailednow(request):
    pagesize = request.query_params.get('pagesize', None)
    paginator = PageNumberPagination()
    print("paginator", paginator)
    month = request.data.get('month', None)
    locationwise = request.data.get('locationwise', None)
    groupby = request.data.get('groupby', None)  # name of categories
    locationname = request.data.get('locationname', None)  # category values
    agency = request.data.get('agency', None)
    print(">>>>>>", locationname)
    cursor = connection.cursor()
    cursorn = connection.cursor()

    clause = f"WHERE "
    clause += f" {locationwise}='{locationname}' " if locationname else ""
    # clause += f" AND bl_agnc_name='{agency}' " if (agency) else ""
    str1=''
    if agency in  ('Fluent Grid','Fluentgrid'):
        str1 += f"AND bl_agnc_name in ('Fluent Grid','Fluentgrid')"
    elif agency in  ('DATA INGENIOUS', 'Data Ingenious'):
        str1 += f" AND bl_agnc_name in ('DATA INGENIOUS', 'Data Ingenious')"
    elif agency:
        str1 += f"AND bl_agnc_name='{agency}'"
    else:
        pass
    clause+=str1

    query = f'''select {groupby}, mr_id, cons_name, cons_ac_no, rdng_img from readingmaster where extract(month from reading_date_db) = '{date.today().month}' AND extract(year from reading_date_db) = '{date.today().year}' and prsnt_mtr_status !='Meter Defective' and cons_ac_no in(
                select cons_ac_no from readingmaster {clause} and prsnt_mtr_status='Meter Defective' and reading_date_db >= date_trunc('month', current_date - interval '1' month) )group by {groupby}, mr_id, cons_name, cons_ac_no,rdng_img
    '''
    cursor.execute(query)
    results = cursor.fetchall()
    location = []
    try:
        for i in results:
            location.append(
                {"location": i[0],
                 "mrid": i[1],
                 "consname": i[2],
                 "consaccno": i[3],
                 "meterimg": i[4],
                 })
            # newdata = listfun(newdict)
        if pagesize:
            paginator.page_size = pagesize
        else:
            paginator.page_size = 17000

        result_page = paginator.paginate_queryset(location, request)
        return paginator.get_paginated_response(result_page)
    except:
        return Response([])



#indra-sbpdcl        
@api_view(['POST'])
def custom_sbpdcl_mrreports(request):
    data = request.data
    
    # 1. Extract inputs
    start_date = data.get("start_date")
    end_date = data.get("end_date")
    page = int(data.get("page", 1))
    pagesize = int(data.get("pagesize", 20))
    
    # Handle both "discom" (from your JSON) and "ofc_discom" keys safely
    ofc_discom = data.get("discom") or data.get("ofc_discom") or "SBPDCL"
    
    # Extract Location Filters
    req_zone = data.get("zone")
    req_circle = data.get("circle")
    req_division = data.get("division")
    req_subdivision = data.get("subdivision")
    req_section = data.get("section")

    if not start_date or not end_date:
        return Response({"error": "start_date and end_date are required"}, status=400)

    offset = (page - 1) * pagesize
    table_name = "readingmaster"
    
    # 2. Initialize Base Parameters (Order matches the %s in the WHERE clause base)
    params = [ofc_discom, start_date, end_date]
    clause = ""

    # 3. Dynamic Clause Construction
    # We check if the variable exists AND is not an empty string
    if req_zone:
        clause += " AND ofc_zone = %s "
        params.append(req_zone)
        
    if req_circle:
        clause += " AND ofc_circle = %s "
        params.append(req_circle)
        
    if req_division:
        clause += " AND ofc_division = %s "
        params.append(req_division)
        
    if req_subdivision:
        clause += " AND ofc_subdivision = %s "
        params.append(req_subdivision)
        
    if req_section:
        # print("++++++++++++++++",req_section)
        clause += " AND ofc_section = %s "
        params.append(req_section)

    # 4. Save parameters for the Count Query (before adding limit/offset)
    count_params = list(params)

    # 5. Add Limit/Offset for the Main Query
    params.extend([pagesize, offset])

    cursor = connection.cursor()

    # 6. Main Query
    query = f"""
            WITH stats AS (
                SELECT
                    mr_id,
                    COUNT(*) AS total_readings,
                    COUNT(*) FILTER (WHERE prsnt_mtr_status = 'Ok') AS ok_count,
                    COUNT(*) FILTER (WHERE prsnt_mtr_status = 'Meter Defective') AS MD_count,
                    COUNT(*) FILTER (WHERE prsnt_mtr_status = 'Door Locked') AS DL_count,
                    COUNT(*) FILTER (WHERE rdng_ocr_status = 'Passed' AND prsnt_mtr_status = 'Ok') AS Passed_count,
                    COUNT(*) FILTER (WHERE rdng_ocr_status = 'Failed' AND prsnt_mtr_status = 'Ok') AS Failed_count
                FROM {table_name}
                WHERE ofc_discom = %s 
                  AND reading_date_db::date BETWEEN %s AND %s 
                  AND mr_id <> '' AND LENGTH(mr_id) > 5 
                  {clause} 
                GROUP BY mr_id
            )
            SELECT
                mr_id,
                total_readings,
                ok_count,
                ROUND(100.0 * ok_count / NULLIF(total_readings, 0), 2) AS pct_ok,
                MD_count,
                ROUND(100.0 * MD_count / NULLIF(total_readings, 0), 2) AS pct_meter_defective,
                DL_count,
                ROUND(100.0 * DL_count / NULLIF(total_readings, 0), 2) AS pct_door_locked,
                Passed_count,
                ROUND(100.0 * Passed_count / NULLIF(ok_count, 0), 2) AS pct_ocr_without_exception,
                Failed_count,
                ROUND(100.0 * Failed_count / NULLIF(ok_count, 0), 2) AS pct_ocr_with_exception
            FROM stats ORDER BY mr_id LIMIT %s OFFSET %s;
    """

    cursor.execute(query, params)
    results = dictfetchall(cursor)

    # Debugging: Print valid SQL
    final_sql = query
    for p in params:
        final_sql = final_sql.replace("%s", f"'{p}'", 1)
    # print("Query:-->", final_sql)

    # 7. Count Query (Using the specific count_params list)
    count_sql = f"""
        SELECT COUNT(*)
        FROM (
            SELECT mr_id FROM {table_name} 
            WHERE ofc_discom = %s AND DATE(reading_date_db) BETWEEN %s AND %s 
            {clause} 
            AND mr_id <> '' AND LENGTH(mr_id) > 5 
            GROUP BY mr_id
        ) AS t;
    """
    
    cursor.execute(count_sql, count_params)
    total_count = cursor.fetchone()[0]
    total_pages = (total_count + pagesize - 1) // pagesize

    return Response({
        "status": True,
        "page": page,
        "pagesize": pagesize,
        "total_pages": total_pages,
        "total_records": total_count,
        "data_count": len(results),
        "data": results,
    })



# indra-sbpdcl
@api_view(["POST"])
def reading_details_by_mrid(request):
    mr_id = request.data.get("mr_id")
    prsnt_mtr_status = request.data.get("prsnt_mtr_status") or request.data.get("prsnt_meter_status")
    rdng_ocr_status = request.data.get("rdng_ocr_status") or request.data.get("ocr_status")
    # Clean empty strings
    prsnt_mtr_status = prsnt_mtr_status.strip() if isinstance(prsnt_mtr_status, str) else None
    rdng_ocr_status = rdng_ocr_status.strip() if isinstance(rdng_ocr_status, str) else None
    start_date = request.data.get("start_date")
    end_date = request.data.get("end_date")
    pagesize = int(request.data.get("pagesize", 20))
    page = int(request.data.get("page", 1))
    offset = (page - 1) * pagesize
    # Validation
    if not mr_id:
        return Response({"status": False, "message": "mr_id is required"}, status=400)
    if not start_date or not end_date:
        return Response({"status": False, "message": "start_date and end_date are required"}, status=400)
    try:
        sd = datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        return Response({"status": False, "message": "Dates must be YYYY-MM-DD"}, status=400)
    if sd > ed:
        return Response({"status": False, "message": "start_date cannot be after end_date"}, status=400)
    cursor = connection.cursor()
    # Build WHERE clauses
    where_conditions = [
        "mr_id = %s",
        "reading_date_db::date BETWEEN %s AND %s"
    ]
    params = [mr_id, start_date, end_date]
    if prsnt_mtr_status:
        where_conditions.append("prsnt_mtr_status = %s")
        params.append(prsnt_mtr_status)
    if rdng_ocr_status:
        where_conditions.append("rdng_ocr_status = %s")
        params.append(rdng_ocr_status)
    where_clause = " AND ".join(where_conditions)
    # --- COUNT QUERY ---
    count_query = f"SELECT COUNT(*) FROM readingmaster WHERE {where_clause}"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    # If no data return here
    if total_count == 0:
        # Print SQL for debugging
        print("NO DATA SQL:", cursor.mogrify(count_query, params).decode())
        return Response({"status": True, "message": "No data found", "data": []})
    total_pages = (total_count + pagesize - 1) // pagesize
    query = f"""
        SELECT rdng_date AS date,
               mr_ph_no AS mobile_number,
               con_mtr_sl_no AS meter_slno,
               cons_ac_no AS consumer_id,
               geo_lat AS geo_lat,
               geo_long AS geo_long,
               rdng_img AS reading_image,
               prsnt_mtr_status AS meter_status,
               rdng_ocr_status AS ocr_status
        FROM readingmaster
        WHERE {where_clause}
        ORDER BY reading_date_db DESC
        LIMIT %s OFFSET %s
    """
    final_params = params + [pagesize, offset]
    cursor.execute(query, final_params)
    print("\nFINAL SQL:\n", cursor.mogrify(query, final_params).decode())

    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return Response({
        "status": True,
        "message": f"{len(data)} records fetched",
        "mr_id": mr_id,
        "total_records": total_count,
        "total_pages": total_pages,
        "page": page,
        "pagesize": pagesize,
        "data": data
    })


#sbpdcl
# @api_view(["POST"])
# def reading_details_by_mrid(request):
#     mr_id = request.data.get("mr_id")
#     start_date = request.data.get("start_date")
#     end_date = request.data.get("end_date")
#     pagesize = int(request.data.get("pagesize", 20))
#     page = int(request.data.get("page", 1))
#     offset = (pagesize * page) - pagesize
#     if not mr_id:
#         return Response({"status": False, "message": "mr_id is required"})
#     if not start_date or not end_date:
#         return Response({"status": False, "message": "start_date and end_date are required"})
 
#     cursor = connection.cursor()
#     count_query = """
#         SELECT COUNT(*) FROM readingmaster WHERE mr_id = %sAND reading_date_db BETWEEN %s AND %s and mr_id <> '' AND LENGTH(mr_id) > 5
#     """
#     cursor.execute(count_query, [mr_id, start_date, end_date])
#     total_count = cursor.fetchone()[0]
#     if total_count == 0:
#         return Response({
#             "status": True,
#             "message": "No data found for given MR ID and date range",
#             "data": []
#         })
#     total_pages = (total_count + pagesize - 1) // pagesize
 
#     query = """
#         SELECT rdng_date AS date,mr_ph_no AS mobile_number,con_mtr_sl_no AS meter_slno,cons_ac_no AS consumer_id,geo_lat AS geo_lat,geo_long AS geo_long,rdng_img AS reading_image
#         FROM readingmaster
#         WHERE mr_id = %s AND reading_date_db BETWEEN %s AND %s AND mr_id <> '' AND LENGTH(mr_id) > 5 ORDER BY reading_date_db DESC LIMIT %s OFFSET %s
#     """
#     params = [mr_id, start_date, end_date, pagesize, offset]
#     cursor.execute(query, params)
#     columns = [col[0] for col in cursor.description]
#     data = [dict(zip(columns, row)) for row in cursor.fetchall()]
#     final_sql = query
#     for p in params:
#         final_sql = final_sql.replace("%s", f"'{p}'", 1)
 
#     print("QUERY:-->>>>", final_sql)
#     return Response({
#         "status": True,
#         "message": f"{len(data)} records fetched successfully",
#         "mr_id": mr_id,
#         "total_records": total_count,
#         "total_pages":total_pages,
#         "page": page,
#         "pagesize": pagesize,
#         "data": data,
#         # "executed_query": final_sql,  # ⬅ returned in response also
#     })
 

#Sanjeev
@api_view(['POST'])
def custom_discom_mrreports(request):
    data = request.data
    selected_month=data.get('date')
    year,month = selected_month.split('-')    
    print(month,"month")
    print(year,"year")
    print(selected_month,"selected_month")
    today = datetime.now()
    this_month = today.strftime("%m")
    print("thisMOnth:",this_month)
    previous_month = (today - timedelta(days=today.day)).strftime("%m")
    print("previous_month:",previous_month)
    
    


    # where conditions
    clause = f"WHERE "
    for key, value in data.items():
        if key == 'date' and value!="":
            clause += f"extract(month from reading_date_db)='{month}' and extract(year from reading_date_db)='{year}' AND "
        elif key == 'enddate' and value!="":
            clause += f"extract(day from reading_date_db) BETWEEN '{data['startdate']}' AND '{value}' AND "
        elif key in ('ofc_discom', 'ofc_zone', 'ofc_division', 'ofc_subdivision', 'ofc_circle', 'ofc_section', 'bl_agnc_name') and value!="":
            if key == "bl_agnc_name" and value in  ('Fluent Grid','Fluentgrid'):
                clause += f"{key} in ('Fluent Grid','Fluentgrid') AND "
            elif  key == "bl_agnc_name" and value in  ('DATA INGENIOUS', 'Data Ingenious'):
                clause += f"{key} in ('DATA INGENIOUS', 'Data Ingenious') AND "
            else:
                clause += f"{key}='{value}' AND "
        else:
            continue
    clause += f"{data['latest'][0]}!='' and mr_id not in ('mrctest','mrDanish') and bl_agnc_name!='BCITS'  "

    # selections
    clause2 = f"WHERE "
    for keys in data['selection']:
        if keys=='ocr50':
            clause2 += f"(CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END) < 50.0"

    cursor = connection.cursor()
    
    year,month = selected_month.split('-')
    tablename = "readingmaster" if month in {this_month, previous_month} else "prevmonthsdata"


    sql_query = f'''
        with main_query as (
            select
                mr_id,
                {data['latest'][0]},
                COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS okcount,
                COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS ocrPassed,
                COUNT(CASE WHEN rdng_ocr_status = 'Failed' THEN 1 END) AS ocrFailed,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Image blur' THEN 1 ELSE 0 END) AS imageBlur,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Incorrect Reading' THEN 1 ELSE 0 END) AS incorrectReading,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Meter Dirty' THEN 1 ELSE 0 END) AS meterDirty,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'No Exception Found' THEN 1 ELSE 0 END) AS noExcepFound,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Spoofed Image' THEN 1 ELSE 0 END) AS spoofedImage,
                SUM(CASE WHEN rdng_ocr_status = 'Failed' AND prsnt_rdng_ocr_excep = '' THEN 1 ELSE 0 END) AS blanks	
            FROM 
                {tablename}
            {'' if 'sectionname' !=data['latest'][0] else " join ( SELECT DISTINCT sectioncode, MAX(sectionname) AS sectionname FROM office GROUP BY sectioncode) o ON ofc_section = o.sectioncode"}
            {clause}
            GROUP BY 
                mr_id, {data['latest'][0]}
        )
        select
                mr_id,
                {data['latest'][0]},
                okcount,
                ocrPassed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withoutExcepPercen,
                ocrFailed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrFailed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withExcepPercen,
                imageBlur,
                incorrectReading,
                meterDirty,
                noExcepFound,
                spoofedImage,
                blanks
        from main_query
        {'' if len(data['selection'])==0 else clause2}
        order by {data['latest'][0]},withoutExcepPercen asc
        '''
    print("QUERY:",sql_query)    
    cursor.execute(sql_query)
    results = dictfetchall(cursor)

    response = {
        "data" : results,
    }
    return Response(response)

#Sanjeev
@api_view(['POST'])
def custom_discom_locreports(request):
    data = request.data
    selected_month=data.get('date')
    year,month = selected_month.split('-')    
    print(month,"month")
    print(year,"year")
    print(selected_month,"selected_month")
    today = datetime.now()
    this_month = today.strftime("%m")
    print("thisMOnth:",this_month)
    previous_month = (today - timedelta(days=today.day)).strftime("%m")
    print("previous_month:",previous_month)
    print("data:\n", data)

    # where conditions
    clause = f"WHERE "
    for key, value in data.items():
        if key == 'date' and value!="":
            clause += f"extract(month from reading_date_db)='{value.split('-')[1]}' and extract(year from reading_date_db)={value.split('-')[0]} AND "
        elif key == 'enddate' and value!="":
            clause += f"extract(day from reading_date_db) BETWEEN '{data['startdate']}' AND '{value}' AND "
        elif key in ('ofc_discom', 'ofc_zone', 'ofc_division', 'ofc_subdivision', 'ofc_circle', 'ofc_section', 'bl_agnc_name') and value!="":
            if key == "bl_agnc_name" and value in  ('Fluent Grid','Fluentgrid'):
                clause += f"{key} in ('Fluent Grid','Fluentgrid') AND "
            elif  key == "bl_agnc_name" and value in  ('DATA INGENIOUS', 'Data Ingenious'):
                clause += f"{key} in ('DATA INGENIOUS', 'Data Ingenious') AND "
            else:
                clause += f"{key}='{value}' AND "
        else:
            continue
    # if clause[-4:] == 'AND ':
    #     clause = clause[:-4]
    clause += f"{data['latest'][0]}!='' and bl_agnc_name!='BCITS'  "

    # selections
    clause2 = f"WHERE "
    for keys in data['selection']:
        if keys=='ocr50':
            clause2 += f"(CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END) < 50.0"

    cursor = connection.cursor()
    
    year,month = selected_month.split('-')
    tablename = "readingmaster" if month in {this_month, previous_month} else "prevmonthsdata"
    
    sql_query = f'''
        with main_query as (
            select
                {data['latest'][0]},
                COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS okcount,
                COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS ocrPassed,
                COUNT(CASE WHEN rdng_ocr_status = 'Failed' THEN 1 END) AS ocrFailed,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Image blur' THEN 1 ELSE 0 END) AS imageBlur,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Incorrect Reading' THEN 1 ELSE 0 END) AS incorrectReading,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Meter Dirty' THEN 1 ELSE 0 END) AS meterDirty,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'No Exception Found' THEN 1 ELSE 0 END) AS noExcepFound,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Spoofed Image' THEN 1 ELSE 0 END) AS spoofedImage,
                SUM(CASE WHEN rdng_ocr_status = 'Failed' AND prsnt_rdng_ocr_excep = '' THEN 1 ELSE 0 END) AS blanks	
            FROM 
                {tablename}
            {'' if 'sectionname' !=data['latest'][0] else " join ( SELECT DISTINCT sectioncode, MAX(sectionname) AS sectionname FROM office GROUP BY sectioncode) o ON ofc_section = o.sectioncode"}
            {clause}
            GROUP BY 
                {data['latest'][0]}
        )
        select
                {data['latest'][0]},
                okcount,
                ocrPassed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withoutExcepPercen,
                ocrFailed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrFailed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withExcepPercen,
                imageBlur,
                incorrectReading,
                meterDirty,
                noExcepFound,
                spoofedImage,
                blanks
        from main_query
        {'' if len(data['selection'])==0 else clause2}
        order by withoutExcepPercen asc
        '''
    print("\n query:\n", sql_query)
    cursor.execute(sql_query)
    results = dictfetchall(cursor)

    response = {
        "data" : results,
    }
    return Response(response)




#Sanjeev
@api_view(['POST'])
def custom_discom_divreports(request):
    data = request.data
    print("data:\n", data)
    selected_month=data.get('date')
    year,month = selected_month.split('-')    
    print(month,"month")
    print(year,"year")
    print(selected_month,"selected_month")
    today = datetime.now()
    this_month = today.strftime("%m")
    print("thisMOnth:",this_month)
    previous_month = (today - timedelta(days=today.day)).strftime("%m")
    print("previous_month:",previous_month)

    # where conditions
    clause = f"WHERE "
    for key, value in data.items():
        if key == 'date' and value!="":
            clause += f"extract(month from reading_date_db)='{value.split('-')[1]}' and extract(year from reading_date_db)={value.split('-')[0]} AND "
        elif key == 'enddate' and value!="":
            clause += f"extract(day from reading_date_db) BETWEEN '{data['startdate']}' AND '{value}' AND "
        elif key in ('ofc_discom', 'ofc_zone', 'ofc_division', 'ofc_subdivision', 'ofc_circle', 'ofc_section', 'bl_agnc_name') and value!="":
            if key == "bl_agnc_name" and value in  ('Fluent Grid','Fluentgrid'):
                clause += f"{key} in ('Fluent Grid','Fluentgrid') AND "
            elif  key == "bl_agnc_name" and value in  ('DATA INGENIOUS', 'Data Ingenious'):
                clause += f"{key} in ('DATA INGENIOUS', 'Data Ingenious') AND "
            else:
                clause += f"{key}='{value}' AND "
        else:
            continue
    # if clause[-4:] == 'AND ':
    #     clause = clause[:-4]
    clause += f"ofc_division!='' AND ofc_subdivision!='' and bl_agnc_name!='BCITS'  "

    # selections
    clause2 = f"WHERE "
    for keys in data['selection']:
        if keys=='ocr50':
            clause2 += f"(CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END) < 50.0"

    cursor = connection.cursor()
    
    year,month = selected_month.split('-')
    tablename = "readingmaster" if month in {this_month, previous_month} else "prevmonthsdata"
    
    sql_query = f'''
        with main_query as (
            select
                ofc_division, ofc_subdivision,
                COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS okcount,
                COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS ocrPassed,
                COUNT(CASE WHEN rdng_ocr_status = 'Failed' THEN 1 END) AS ocrFailed,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Image blur' THEN 1 ELSE 0 END) AS imageBlur,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Incorrect Reading' THEN 1 ELSE 0 END) AS incorrectReading,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Meter Dirty' THEN 1 ELSE 0 END) AS meterDirty,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'No Exception Found' THEN 1 ELSE 0 END) AS noExcepFound,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Spoofed Image' THEN 1 ELSE 0 END) AS spoofedImage,
                SUM(CASE WHEN rdng_ocr_status = 'Failed' AND prsnt_rdng_ocr_excep = '' THEN 1 ELSE 0 END) AS blanks	
            FROM 
                {tablename}
            {clause}
            GROUP BY 
                ofc_division, ofc_subdivision
        )
        select
                ofc_division, ofc_subdivision,
                okcount,
                ocrPassed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withoutexceppercen,
                ocrFailed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrFailed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withexceppercen,
                imageBlur,
                incorrectReading,
                meterDirty,
                noExcepFound,
                spoofedImage,
                blanks
        from main_query
        {'' if len(data['selection'])==0 else clause2}
        order by ofc_division, withoutexceppercen asc
        '''
    print("\n query:\n", sql_query)
    cursor.execute(sql_query)
    results = dictfetchall(cursor)

    response = {
        "data" : results,
    }
    return Response(response)


#Sanjeev
@api_view(['POST'])
def custom_discom_agncreports(request):
    data = request.data
    print("data:\n", data)
    selected_month=data.get('date')
    year,month = selected_month.split('-')    
    print(month,"month")
    print(year,"year")
    print(selected_month,"selected_month")
    today = datetime.now()
    this_month = today.strftime("%m")
    print("thisMOnth:",this_month)
    previous_month = (today - timedelta(days=today.day)).strftime("%m")
    print("previous_month:",previous_month)

    # where conditions
    clause = f"WHERE "
    for key, value in data.items():
        if key == 'date' and value!="":
            clause += f"extract(month from reading_date_db)='{value.split('-')[1]}' and extract(year from reading_date_db)={value.split('-')[0]} AND "
        elif key == 'enddate' and value!="":
            clause += f"extract(day from reading_date_db) BETWEEN '{data['startdate']}' AND '{value}' AND "
        elif key in ('ofc_discom', 'ofc_zone', 'ofc_division', 'ofc_subdivision', 'ofc_circle', 'ofc_section', 'bl_agnc_name') and value!="":
            clause += f"{key}='{value}' AND "
        else:
            continue
    # if clause[-4:] == 'AND ':
    #     clause = clause[:-4]
    clause += f"bl_agnc_name!='' and bl_agnc_name!='BCITS' "

    # selections
    clause2 = f"WHERE "
    for keys in data['selection']:
        if keys=='ocr50':
            clause2 += f"(CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END) < 50.0"

    cursor = connection.cursor()
    
    year,month = selected_month.split('-')
    tablename = "readingmaster" if month in {this_month, previous_month} else "prevmonthsdata"
    sql_query = f'''
        with main_query as (
            select
                CASE
                    WHEN bl_agnc_name IN ('DATA INGENIOUS', 'Data Ingenious') THEN 'Data Ingenious'
                    WHEN bl_agnc_name IN ('Fluent Grid','Fluentgrid') THEN 'Fluentgrid'
                    ELSE bl_agnc_name
                END AS normalized_agnc_name,
                COUNT(CASE WHEN prsnt_mtr_status = 'Ok' THEN 1 END) AS okcount,
                COUNT(CASE WHEN rdng_ocr_status = 'Passed' THEN 1 END) AS ocrPassed,
                COUNT(CASE WHEN rdng_ocr_status = 'Failed' THEN 1 END) AS ocrFailed,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Image blur' THEN 1 ELSE 0 END) AS imageBlur,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Incorrect Reading' THEN 1 ELSE 0 END) AS incorrectReading,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Meter Dirty' THEN 1 ELSE 0 END) AS meterDirty,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'No Exception Found' THEN 1 ELSE 0 END) AS noExcepFound,
                SUM(CASE WHEN prsnt_rdng_ocr_excep = 'Spoofed Image' THEN 1 ELSE 0 END) AS spoofedImage,
                SUM(CASE WHEN rdng_ocr_status = 'Failed' AND prsnt_rdng_ocr_excep = '' THEN 1 ELSE 0 END) AS blanks	
            FROM 
                {tablename}
            {clause}
            GROUP BY 
                normalized_agnc_name
        )
        select
                normalized_agnc_name,
                okcount,
                ocrPassed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrPassed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withoutexceppercen,
                ocrFailed,
                CASE WHEN okcount = 0 THEN 0 ELSE ROUND(ocrFailed::NUMERIC / okcount::NUMERIC * 100, 2) END AS withexceppercen,
                imageBlur,
                incorrectReading,
                meterDirty,
                noExcepFound,
                spoofedImage,
                blanks
        from main_query
        {'' if len(data['selection'])==0 else clause2}
        order by withoutexceppercen asc
        '''
    print("\n query:\n", sql_query)
    cursor.execute(sql_query)
    results = dictfetchall(cursor)

    response = {
        "data" : results,
    }
    return Response(response)
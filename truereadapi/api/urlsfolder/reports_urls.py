from django.urls import path,include
from api.viewsfolder import reports_views as views

urlpatterns=[ 

     path('getocraccuracydata/', views.getocraccuracydata,name='getocraccuracydata'), #updated 1
#     path('getocraccuracyrep/', views.getOCRAccuracyreports,name='getocraccuracyrep'),          #
    path('mrwiseaccuracyreport/', views.getMRwiseAccuracyreportfast,name='mrwiseaccuracyreport'),   #2 
    path('metereportsectionwise/', views.metereportsectionwise,name='metereportsectionwise'),   # 3rd update
    path('monthwiseocraccuracy/', views.monthwiseocraccuracy,name='monthwiseocraccuracy'),        # 4   
    path('mrmonthwiseocraccuracy/', views.mrmonthwiseocraccuracy,name='mrmonthwiseocraccuracy'),  # 5   
    path('newsection/', views.newsection, name='newsection'), # new section
    path('getmeterstatus/', views.get_meter_status, name='get_meter_status'), # get_meter_status
    path('getexception/', views.get_exception, name='get_exception'), # new section

    path('filterdiscom/', views.filter_discom, name='filter_discom'), #  discom filter
    path('filteragency/', views.filter_agency, name='filter_agency'), # filter agency
    path('filtermrid/', views.filter_mrid, name='filter_mrid'), # filter mr for agency
    path('sectionabnorm/', views.sectionabnorm, name='sectionabnorm'), # section for filter abnormality
    path('mrunitsection/', views.mrunitsection, name='mrunitsection'), # section for mr_unit
    path('newsubdivision/', views.subdivision, name='subdivision'), # section for mr_unit
    path('newsectionunit/', views.newsectionunit, name='newsectionunit'), # section for mr_unit
    path('getnewagency/', views.get_new_agency, name='get_new_agency'), # get new_agency 

    path('listofconsumersbilled/', views.listofconsumersbilled, name='listofconsumersbilled'),       #6
    path('listofconsumersbillok/', views.listofconsumersbillok, name='listofconsumersbillok'),       #7
    path('consmbillocrwithok/', views.consmbillocrwithok, name='consmbillocrwithok'),                #8
    path('consmbillocrwithexcept/', views.consmbillocrwithexcept, name='consmbillocrwithexcept'),    #9
    path('exceptionsummary/', views.exceptionsummary, name='exceptionsummary'),                      #10
    path('listconsmwithmd/', views.listconsmwithmd, name='listconsmwithmd'),                         #11
    path('listconsmwithdl/', views.listconsmwithdl, name='listconsmwithdl'),                         #12
    path('abnormalitieslist/', views.abnormalitieslist, name='abnormalitieslist'),                   #13
    path('mrwiseperformancereport/', views.mrwiseperformancereport, name='mrwiseperformancereport'), #14
    path('monthwiseperformance/', views.monthwiseperformance, name='monthwiseperformance'),          #15
    path('locwiseperformancereport/', views.locwiseperformancereport, name='locwiseperformancereport'), #16
    path('agencyperformancereport/', views.agencyperformancereport, name='agencyperformancereport'), #17
    # path('mothwisecomreport/', views.mothwisecomreport, name='mothwisecomreport'),                 #18
    path('mothwisecomreportsabnorm/', views.mothwisecomreports, name='mothwisecomreports'),          #18 - update
    path('mothwisecomreportsexcpt/', views.mothwisecomreports, name='mothwisecomreports'),           #19 - 
    path('visionocrfailedpremon/', views.visionocrfailedpremon, name='visionocrfailedpremonth'),     #20
    path('visionocrpassedpremon/', views.visionocrpassedpremon, name='visionocrpassedpremon'),       #21
    path('defectivemtraging/', views.defectivemtraging, name='defectivemtraging'),                   #22
    path('dlmeteraging/', views.dlmeteraging, name='dlmeteraging'),                                  #23
    path('defectprevmonthandoknow/', views.defectprevmonthandoknow, name='defectprevmonthandoknow'), #24                                 #23
    path('okprevmonbutfailednow/', views.okprevmonbutfailednow, name='okprevmonbutfailednow'),       #25                                 #23
    path('customdiscommrreport/', views.custom_discom_mrreports, name='customdiscommrwisereport'),    #26
    path('customsbpdclmrreport/', views.custom_sbpdcl_mrreports, name='customsbpdclmrreport'),    #26
    path('customsbpdclmrdata/', views.reading_details_by_mrid, name='customsbpdclmrdata'),    #26
    path('customdiscomlocreport/', views.custom_discom_locreports, name='customdiscomlocatreport'),    #27
    path('customdiscomdivreport/', views.custom_discom_divreports, name='customdiscomdivreport'),    #28
    path('customdiscomagncreport/', views.custom_discom_agncreports, name='customdiscomagncreport'),    #29
    ]
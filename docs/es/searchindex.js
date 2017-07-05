Search.setIndex({docnames:["api","api/catatom2osm","api/csvtools","api/download","api/hgwnames","api/layer","api/main","api/modules","api/osm","api/osmxml","api/setup","api/test","api/test.test_csvtools","api/test.test_download","api/test.test_hgwnames","api/test.test_layer","api/test.test_osm","api/test.test_translate","api/test.unittest_main","api/translate","changes","coverage","genindex","index","readme"],envversion:50,filenames:["api.rst","api/catatom2osm.rst","api/csvtools.rst","api/download.rst","api/hgwnames.rst","api/layer.rst","api/main.rst","api/modules.rst","api/osm.rst","api/osmxml.rst","api/setup.rst","api/test.rst","api/test.test_csvtools.rst","api/test.test_download.rst","api/test.test_hgwnames.rst","api/test.test_layer.rst","api/test.test_osm.rst","api/test.test_translate.rst","api/test.unittest_main.rst","api/translate.rst","changes.rst","coverage.rst","genindex.rst","index.rst","readme.rst"],objects:{"":{catatom2osm:[1,0,0,"-"],csvtools:[2,0,0,"-"],download:[3,0,0,"-"],hgwnames:[4,0,0,"-"],layer:[5,0,0,"-"],main:[6,0,0,"-"],osm:[8,0,0,"-"],osmxml:[9,0,0,"-"],setup:[10,0,0,"-"],test:[11,0,0,"-"],translate:[19,0,0,"-"]},"catatom2osm.CatAtom2Osm":{exit:[1,2,1,""],export_layer:[1,2,1,""],get_atom_file:[1,2,1,""],get_crs_from_gml:[1,2,1,""],merge_address:[1,2,1,""],osm_from_layer:[1,2,1,""],path:[1,3,1,""],qgs:[1,3,1,""],read_gml_layer:[1,2,1,""],run:[1,2,1,""],split_building_in_tasks:[1,2,1,""],write_osm:[1,2,1,""],zip_code:[1,3,1,""]},"download.ProgressBar":{update:[3,2,1,""]},"layer.BaseLayer":{"export":[5,2,1,""],append:[5,2,1,""],copy_feature:[5,2,1,""],join_field:[5,2,1,""],reproject:[5,2,1,""],search:[5,2,1,""],translate_field:[5,2,1,""]},"layer.ConsLayer":{clean:[5,2,1,""],index_of_building_and_parts:[5,2,1,""],is_building:[5,5,1,""],is_part:[5,5,1,""],is_pool:[5,5,1,""],merge_building_parts:[5,2,1,""],merge_greatest_part:[5,2,1,""],move_address:[5,2,1,""],remove_duplicated_holes:[5,2,1,""],remove_outside_parts:[5,2,1,""],remove_parts_below_ground:[5,2,1,""],set_tasks:[5,2,1,""]},"layer.DebugWriter":{add_point:[5,2,1,""]},"layer.Point":{boundingBox:[5,2,1,""],get_angle_with_context:[5,2,1,""]},"layer.PolygonLayer":{add_topological_points:[5,2,1,""],clean:[5,2,1,""],clean_duplicated_nodes_in_polygons:[5,2,1,""],explode_multi_parts:[5,2,1,""],get_adjacents_and_features:[5,2,1,""],get_duplicates:[5,2,1,""],get_parents_per_vertex_and_features:[5,2,1,""],get_vertices:[5,2,1,""],merge_adjacents:[5,2,1,""],merge_duplicates:[5,2,1,""],simplify:[5,2,1,""]},"layer.ZoningLayer":{clasify_zoning:[5,5,1,""],set_labels:[5,2,1,""]},"osm.Element":{is_uploaded:[8,2,1,""],new_index:[8,2,1,""]},"osm.Node":{geometry:[8,2,1,""]},"osm.Osm":{merge_duplicated:[8,2,1,""],new_indexes:[8,2,1,""],nodes:[8,3,1,""],relations:[8,3,1,""],replace:[8,2,1,""],ways:[8,3,1,""]},"osm.Relation":{Member:[8,1,1,""],append:[8,2,1,""],geometry:[8,2,1,""],replace:[8,2,1,""]},"osm.Relation.Member":{ref:[8,3,1,""],type:[8,3,1,""]},"osm.Way":{clean_duplicated_nodes:[8,2,1,""],geometry:[8,2,1,""],replace:[8,2,1,""],search_node:[8,2,1,""]},"test.test_csvtools":{TestCsvTools:[12,1,1,""]},"test.test_csvtools.TestCsvTools":{test_csv2dict:[12,2,1,""],test_dict2csv:[12,2,1,""]},"test.test_download":{TestGetResponse:[13,1,1,""],TestProgressBar:[13,1,1,""],TestWget:[13,1,1,""]},"test.test_download.TestGetResponse":{test_get_response_bad:[13,2,1,""],test_get_response_ok:[13,2,1,""]},"test.test_download.TestProgressBar":{test_init:[13,2,1,""],test_update100:[13,2,1,""],test_update:[13,2,1,""]},"test.test_download.TestWget":{test_wget:[13,2,1,""]},"test.test_hgwnames":{TestHgwnames:[14,1,1,""]},"test.test_hgwnames.TestHgwnames":{test_get_names:[14,2,1,""],test_parse:[14,2,1,""]},"test.test_layer":{TestAddressLayer:[15,1,1,""],TestBaseLayer:[15,1,1,""],TestConsLayer:[15,1,1,""],TestDebugWriter:[15,1,1,""],TestParcelLayer:[15,1,1,""],TestPoint:[15,1,1,""],TestPolygonLayer:[15,1,1,""],TestZoningLayer:[15,1,1,""]},"test.test_layer.TestAddressLayer":{setUp:[15,2,1,""],test_append:[15,2,1,""],test_join_field:[15,2,1,""]},"test.test_layer.TestBaseLayer":{setUp:[15,2,1,""],test_append_all_fields:[15,2,1,""],test_append_with_query:[15,2,1,""],test_append_with_rename:[15,2,1,""],test_copy_feature_all_fields:[15,2,1,""],test_copy_feature_with_rename:[15,2,1,""],test_export_default:[15,2,1,""],test_export_other:[15,2,1,""],test_reproject:[15,2,1,""],test_translate_field:[15,2,1,""]},"test.test_layer.TestConsLayer":{setUp:[15,2,1,""],test_add_topological_points:[15,2,1,""],test_append_building:[15,2,1,""],test_append_buildingpart:[15,2,1,""],test_append_othercons:[15,2,1,""],test_index_of_building_and_parts:[15,2,1,""],test_is_building:[15,2,1,""],test_is_part:[15,2,1,""],test_is_pool:[15,2,1,""],test_merge_building_parts:[15,2,1,""],test_merge_greatest_part:[15,2,1,""],test_move_address:[15,2,1,""],test_remove_duplicated_holes_buildings:[15,2,1,""],test_remove_duplicated_holes_parts:[15,2,1,""],test_remove_outside_parts:[15,2,1,""],test_remove_parts_below_ground:[15,2,1,""],test_set_tasks:[15,2,1,""],test_simplify1:[15,2,1,""],test_simplify2:[15,2,1,""]},"test.test_layer.TestDebugWriter":{test_add_point:[15,2,1,""],test_init:[15,2,1,""]},"test.test_layer.TestParcelLayer":{test_init:[15,2,1,""],test_not_empty:[15,2,1,""]},"test.test_layer.TestPoint":{test_boundigBox:[15,2,1,""],test_is_corner_with_context:[15,2,1,""]},"test.test_layer.TestPolygonLayer":{setUp:[15,2,1,""],test_clean_duplicated_nodes_in_polygons:[15,2,1,""],test_explode_multi_parts:[15,2,1,""],test_get_duplicates:[15,2,1,""],test_get_parents_per_vertex_and_features:[15,2,1,""],test_get_vertices:[15,2,1,""],test_merge_duplicates:[15,2,1,""]},"test.test_layer.TestZoningLayer":{setUp:[15,2,1,""],test_clasify_zoning:[15,2,1,""],test_get_adjacents_and_features:[15,2,1,""],test_merge_adjacents:[15,2,1,""],test_set_labels:[15,2,1,""]},"test.test_osm":{OsmTestCase:[16,1,1,""],TestOsm:[16,1,1,""],TestOsmElement:[16,1,1,""],TestOsmMultiPolygon:[16,1,1,""],TestOsmNode:[16,1,1,""],TestOsmPolygon:[16,1,1,""],TestOsmRelation:[16,1,1,""],TestOsmWay:[16,1,1,""]},"test.test_osm.OsmTestCase":{setUp:[16,2,1,""]},"test.test_osm.TestOsm":{test_getattr:[16,2,1,""],test_init:[16,2,1,""],test_merge_duplicated:[16,2,1,""],test_new_indexes:[16,2,1,""],test_properties:[16,2,1,""],test_replace:[16,2,1,""]},"test.test_osm.TestOsmElement":{test_init:[16,2,1,""],test_is_uploaded:[16,2,1,""],test_new_index:[16,2,1,""]},"test.test_osm.TestOsmMultiPolygon":{test_init:[16,2,1,""]},"test.test_osm.TestOsmNode":{test_eq:[16,2,1,""],test_geometry:[16,2,1,""],test_getitem:[16,2,1,""],test_init:[16,2,1,""],test_ne:[16,2,1,""],test_str:[16,2,1,""]},"test.test_osm.TestOsmPolygon":{test_init:[16,2,1,""]},"test.test_osm.TestOsmRelation":{test_append:[16,2,1,""],test_eq:[16,2,1,""],test_geometry:[16,2,1,""],test_init:[16,2,1,""],test_member_eq:[16,2,1,""],test_member_ne:[16,2,1,""],test_ne:[16,2,1,""],test_ref:[16,2,1,""],test_replace:[16,2,1,""],test_type:[16,2,1,""]},"test.test_osm.TestOsmWay":{test_clean_duplicated_nodes:[16,2,1,""],test_eq:[16,2,1,""],test_geometry:[16,2,1,""],test_init:[16,2,1,""],test_replace:[16,2,1,""],test_search_node:[16,2,1,""]},"test.test_translate":{TestTranslate:[17,1,1,""]},"test.test_translate.TestTranslate":{test_address_tags:[17,2,1,""],test_all_tags:[17,2,1,""],test_building_tags:[17,2,1,""]},"test.unittest_main":{QgsSingleton:[18,1,1,""]},catatom2osm:{CatAtom2Osm:[1,1,1,""],list_municipalities:[1,4,1,""]},csvtools:{csv2dict:[2,4,1,""],dict2csv:[2,4,1,""]},download:{ProgressBar:[3,1,1,""],get_response:[3,4,1,""],wget:[3,4,1,""]},hgwnames:{get_translations:[4,4,1,""],parse:[4,4,1,""]},layer:{AddressLayer:[5,1,1,""],BaseLayer:[5,1,1,""],ConsLayer:[5,1,1,""],DebugWriter:[5,1,1,""],ParcelLayer:[5,1,1,""],Point:[5,1,1,""],PolygonLayer:[5,1,1,""],ZoningLayer:[5,1,1,""],get_attributes:[5,4,1,""],is_inside:[5,4,1,""]},osm:{Element:[8,1,1,""],MultiPolygon:[8,1,1,""],Node:[8,1,1,""],Osm:[8,1,1,""],Polygon:[8,1,1,""],Relation:[8,1,1,""],Way:[8,1,1,""]},osmxml:{serialize:[9,4,1,""]},test:{test_csvtools:[12,0,0,"-"],test_download:[13,0,0,"-"],test_hgwnames:[14,0,0,"-"],test_layer:[15,0,0,"-"],test_osm:[16,0,0,"-"],test_translate:[17,0,0,"-"],unittest_main:[18,0,0,"-"]},translate:{address_tags:[19,4,1,""],all_tags:[19,4,1,""],building_tags:[19,4,1,""]}},objnames:{"0":["py","module","Python m\u00f3dulo"],"1":["py","class","Python clase"],"2":["py","method","Python m\u00e9todo"],"3":["py","attribute","Python atributo"],"4":["py","function","Python funci\u00f3n"],"5":["py","staticmethod","Python m\u00e9todo est\u00e1tico"]},objtypes:{"0":"py:module","1":"py:class","2":"py:method","3":"py:attribute","4":"py:function","5":"py:staticmethod"},terms:{"0295603cs6109n":5,"6wi":24,"\u00edndic":[0,23],"a\u00f1ad":20,"class":[1,3,5,8,12,13,14,15,16,17,18],"default":[1,4,5],"else":[1,4],"espa\u00f1ol":[20,23,24],"export":[1,5],"extends":5,"float":5,"for":[1,4,5,8,9,19],"function":1,"import":[1,24],"new":[4,5,8],"return":5,"short":1,"static":5,"this":[1,5],"try":[1,3],"with":[1,4,5,8,18],Esto:24,_cor:[5,18],_part:5,_pi:5,a_dict:2,a_path:1,able:5,abov:5,abreviaturs:4,according:5,acording:5,action:8,acute_thr:5,add:5,add_point:5,add_topological_points:5,address:[1,4,5,19,24],address_lay:4,address_osm:1,address_tags:19,addresslay:[4,5],adds:5,adjacent:5,adjacents:5,adminunitnam:1,advertenci:23,alert:4,algun:20,all:[1,5,19,24],all_tags:[1,19],allow_empty:1,aloj:23,also:5,and:[1,3,4,5,8],angle:5,anoth:5,any:[1,5],api:[1,23],aplic:24,app:1,append:[5,8],application:[1,4,5,10],apply:5,archiv:[20,23,24],are:[1,4,5],aren:5,args:[8,13,15],argument:24,asigns:5,assign:8,assings:5,associat:5,atom:[1,20,23,24],attribut:5,au_id:5,avo:5,ayud:24,b1ol:24,b3n_de_edifici:24,bar:[3,5],bas:[5,8,12,13,14,15,16,17,18],baselay:5,basenam:5,basic:3,bdptz:24,becaus:1,becous:5,been:5,befor:5,below:5,betw:5,bool:[1,4,5],bounding:5,boundingbox:5,box:5,building:[1,5,24],building_osm:1,building_tags:19,buildingpart:1,buildings:[1,5],buildings_import:[],but:5,cadastr:[1,4,5],cadastral:5,cadastralparcel:[1,5],cadastralzoning:[1,5],call:5,cambi:23,cas:[12,13,14,15,16,17],catastr:[20,23,24],catastral:24,catastro_esp:24,catatom2osm:[0,6,24],cath_thr:5,center:5,clasify_zoning:5,cle:5,clean_duplicated_nod:8,clean_duplicated_nodes_in_polygons:5,cleans:5,clos:5,cobertur:[0,23],cod:1,codig:[0,20,23,24],collection:8,comenz:24,command:6,component_href:5,configuration:4,conjunt:[23,24],consecutiv:5,conslay:[5,20],construccion:24,constructions:[5,19],constructs:5,consult:24,contain:[5,8],contains:[1,4],conten:23,contents:7,contorn:20,conventions:4,convert:[1,23,24],coordinat:[5,8],copy:[1,5],copy_featur:5,corn:5,corrections:4,correctly:1,correspondient:24,corresponds:5,coverag:18,creacion:20,creat:[1,4,5,8],critical:24,crs:[1,5],csv2dict:2,csv:[2,4],csv_path:2,csvtools:7,cuestion:20,dat:[1,5,8,9,23,24],dataset:8,deb:24,debug:24,debugging:5,debugwrit:5,defaults:[1,5],degr:5,delet:5,deriv:1,desarroll:20,descarg:[20,24],detect:1,determin:1,devuelt:[1,4],devuelv:[1,4,5],dict2csv:2,dict:[4,5],dictionary:[2,4,5],dicts:5,differs:5,digit:24,digits:1,direccion:[20,24],directori:24,directory:[1,4],discov:0,displays:3,dispon:24,distanc:5,distinct:5,don:[1,4],dos:24,downl:[1,7],driver_nam:[1,5],dup_thr:5,duplicat:5,each:[5,8],edifici:20,ejecut:[0,24],element:8,elements:8,empty:1,encoding:2,encuentr:24,english:23,enough:5,entrad:[20,24],entranc:5,entry:[6,18],equal:5,equivalent:24,error:[20,24],esri:[1,5],exampl:5,exception:[1,3],exclud:5,exists:[1,4,5],exit:1,explode_multi_parts:5,export_lay:1,expression:5,fall:20,fals:[1,3],feat:5,featur:[1,5,19],ficher:[20,24],fid:5,fids:5,field:[4,5],field_nam:5,field_names_subset:5,fields:[1,5,19],fil:[1,2,4,5],filenam:[1,3,5],fin:24,final_attribut:5,final_valu:5,first:8,fiv:1,flag:4,floors:5,fold:4,foo:5,footprint:5,form:5,format:[5,9],from:[1,2,4,5,19],fuent:[1,2,3,4,5,8,9,12,13,14,15,16,17,18,19,20],full:4,func:5,functions:2,fusion:20,gdal:24,generat:1,geom:5,geometri:5,geometry:[5,8],get:[1,3,5],get_adjacents_and_featur:5,get_angle_with_context:5,get_atom_fil:1,get_attribut:5,get_crs_from_gml:1,get_duplicat:5,get_parents_per_vertex_and_featur:5,get_respons:3,get_translations:4,get_vertic:5,ggmmm:[1,24],git:23,github:24,giv:[1,5,8],giving:5,gml:1,gml_path:1,gob:24,great:5,greatest:5,groud:5,ground:5,groups:5,gui:5,hac:20,hav:5,help:[2,8,24],herramient:[23,24],hgwnam:7,highway:4,highway_nam:4,highway_typ:4,highways:4,housenumb:4,housenumber_fn:4,html:24,http:[3,24],https:24,hub:23,identifi:5,idiom:23,implement:8,implic:24,importaci:24,imprim:24,increments:3,index:[5,8,24],index_of_building_and_parts:5,indic:24,individual:24,info:24,inicial:20,inner:[5,8],insid:5,inspire:[1,23,24],instal:24,instalacion:23,instanc:1,integers:5,inval:5,is_building:5,is_empty:1,is_insid:5,is_part:5,is_pool:5,is_upload:8,iso8859:2,its:5,javiersanp:24,join:5,join_field:5,join_field_nam:5,join_fieldsnam:5,josm:20,keywargs:[13,15],kwargs:8,label:5,lambd:5,launch:1,lay:[1,4,7,19],layernam:1,layers:[1,5],leem:23,less:5,lev_abov:5,lev_below:5,level:5,levelnam:5,limit:20,lin:6,list:[1,5,8,24],list_municipaliti:1,local:5,localid:5,locat:[1,4],log:24,log_level:24,low:5,lug:24,main:[1,7,24],manag:1,many:[3,5,8],manzana:5,mas:20,matching:1,may:5,mechanism:5,mejor:20,memb:8,members:[5,8],memory:5,menor:20,mensaj:24,merg:[5,8],merge_address:1,merge_adjacents:5,merge_building_parts:5,merge_duplicat:[5,8],merge_greatest_part:5,meters:5,methodnam:[12,13,14,15,16,17],methods:5,metod:20,minhap:24,mmm:1,mod:5,model:8,modify:8,modul:7,moment:5,mor:5,mov:5,move_address:5,moving:5,muestr:24,muev:20,multipart:5,multipolygon:8,municipaliti:1,municipality:1,municipi:24,nam:[1,4,5],names_lay:4,near:5,nearest:5,necessary:1,nev:8,new_index:8,ningun:24,nivel:24,nod:[5,8,20],nombr:24,non:[1,5,8],not:[5,8],numb:5,object:8,occurenc:8,oficin:24,ogr:5,one:[4,5,8],ones:4,only:5,opcion:24,openstreetmap:[8,24],optional:5,optionally:1,options:1,org:24,original:4,original_attribut:5,original_valu:5,osm:[1,4,5,7,9,19,23,24],osm_from_lay:1,osmtestc:16,osmxml:7,otherconstruction:1,out:[5,8],output:[1,5,9],output_fold:4,outputh:4,outsid:5,overwrit:5,packag:7,pair:[5,8],par:[0,20,23,24],parametr:[1,4,5],parcel:[1,5,24],parcellay:5,parcels:5,parent:5,parents:5,pars:4,parsing:4,part:[5,24],parts:[5,8],path:[1,4,5],pd_id:5,percent:3,point:[5,6,18],points:5,poligono:5,polygon:[5,8],polygonlay:5,polygons:5,pool:5,position:[5,8],postaldescriptor:1,precondition:5,predetermin:24,preferenc:10,prefix:5,previous:4,previously:5,priority:5,prob:24,proces:24,program:24,progress:3,progressb:3,propagat:5,propuest:24,prov:24,prov_cod:1,providerlib:5,provinc:1,provincial:24,prueb:[0,24],pued:24,purposess:5,pyqgis:24,python:[0,24],qgis:[1,5,18,24],qgs:1,qgsapplication:[1,18],qgscoordinatereferencesystem:[1,5],qgsfeatur:5,qgsgeometry:5,qgspoint:5,qgssingleton:18,qgsvectorfilewrit:5,qgsvectorlay:[1,5],query:5,radius:5,rais:[1,3],rap:20,read:[2,4],read_gml_lay:1,reads:4,receiv:5,reduc:[5,20],reescrib:20,ref:8,referenc:5,referent:23,registr:[23,24],relat:2,relation:8,relations:[5,8],remov:5,remove_duplicated_hol:5,remove_outside_parts:5,remove_parts_below_ground:5,renam:5,renaming:5,rep:20,repart:24,replac:[5,8],reproject:5,requisit:23,resolv:5,resolving:5,respons:3,result:24,returns:[1,4,5,8],ring:[5,8],rings:[5,8],rol:8,run:[1,18],runtest:[12,13,14,15,16,17],rustic:5,rustic_zoning:[1,5],rut:24,sal:24,sam:[5,8],script:5,sdgc:5,search:5,search_nod:8,see:5,segment:5,segments:5,seleccion:24,self:1,sequenc:5,serializ:9,servic:1,servici:[23,24],set:[1,5,8,9],set_labels:5,set_tasks:5,sets:1,setup:[7,15,16],shapefil:[1,5],shar:5,sid:24,simplif:20,simplific:20,simplify:5,siti:24,sol:24,som:5,soport:20,sourc:[1,4,5,19],source_lay:5,spanish:1,spanish_cadastr:[],spec:5,specification:5,split_building_in_tasks:1,splits:5,sport:20,standalon:5,step:3,str:[1,4,5],str_format:5,straight:5,straight_thr:5,stream:3,street:4,street_fn:4,string:5,strings:5,sub:24,submodul:7,sum:5,tabl:5,tags:[1,8,19],tags_translation:1,tar:[20,24],target:5,target_crs:5,target_field_nam:5,task:[1,5],tasks:24,termin:24,test:[5,7],test_add_point:15,test_add_topological_points:15,test_address_tags:17,test_all_tags:17,test_append:[15,16],test_append_all_fields:15,test_append_building:15,test_append_buildingpart:15,test_append_othercons:15,test_append_with_query:15,test_append_with_renam:15,test_boundigbox:15,test_building_tags:17,test_clasify_zoning:15,test_clean_duplicated_nod:16,test_clean_duplicated_nodes_in_polygons:15,test_copy_feature_all_fields:15,test_copy_feature_with_renam:15,test_csv2dict:12,test_csvtools:[7,11],test_dict2csv:12,test_downl:[7,11],test_eq:16,test_explode_multi_parts:15,test_export_default:15,test_export_oth:15,test_geometry:16,test_get_adjacents_and_featur:15,test_get_duplicat:15,test_get_nam:14,test_get_parents_per_vertex_and_featur:15,test_get_response_b:13,test_get_response_ok:13,test_get_vertic:15,test_getattr:16,test_getitem:16,test_hgwnam:[7,11],test_index_of_building_and_parts:15,test_init:[13,15,16],test_is_building:15,test_is_corner_with_context:15,test_is_part:15,test_is_pool:15,test_is_upload:16,test_join_field:15,test_lay:[7,11],test_member_eq:16,test_member_n:16,test_merge_adjacents:15,test_merge_building_parts:15,test_merge_duplicat:[15,16],test_merge_greatest_part:15,test_move_address:15,test_n:16,test_new_index:16,test_not_empty:15,test_osm:[7,11],test_p:14,test_properti:16,test_ref:16,test_remove_duplicated_holes_buildings:15,test_remove_duplicated_holes_parts:15,test_remove_outside_parts:15,test_remove_parts_below_ground:15,test_replac:16,test_reproject:15,test_search_nod:16,test_set_labels:15,test_set_tasks:15,test_simplify1:15,test_simplify2:15,test_str:16,test_translat:[7,11],test_translate_field:15,test_typ:16,test_updat:13,test_update100:13,test_wget:13,testaddresslay:15,testbaselay:15,testc:[12,13,14,15,16,17],testconslay:15,testcsvtools:12,testdebugwrit:15,testgetrespons:13,testhgwnam:14,testosm:16,testosmelement:16,testosmmultipolygon:16,testosmnod:16,testosmpolygon:16,testosmrelation:16,testosmway:16,testparcellay:15,testpoint:15,testpolygonlay:15,testprogressb:13,testtranslat:17,testwget:13,testzoninglay:15,text:[3,5],than:5,that:[1,5],the:[1,3,4,5,8],ther:[4,5],they:5,thoroughfarenam:1,tim:3,tip:[1,4],tn_id:5,tod:24,too:5,tool:1,topolog:20,topological:5,total:3,traduccion:20,transform:[4,5],translat:[1,5,7],translate_field:5,translati:19,translation:5,translations:[4,5,19],tri:1,tru:[1,5,8],two:5,type:8,types:4,ubuntu:24,underscor:5,uniqu:[5,8],unittest:[0,12,13,14,15,16,17],unittest_main:[7,11],updat:3,uplo:8,upload:8,urban:5,urban_zoning:[1,5],url:[1,3],used:5,uso:23,utility:5,valid:20,valor:[1,4],valu:[4,5],vector:1,version:[20,24],vertex:5,vertexs:5,vertic:5,visibl:8,warning:24,was:[4,5],way:8,ways:8,web:24,webinspir:24,wget:3,wher:[1,4],wiki:24,will:5,within:5,without:5,witn:8,wkbmultipolygon:5,wkbpolygon:5,work:5,writ:[2,4,5],write_osm:1,www:24,xlink:5,xml:[1,9],you:5,zip:1,zip_cod:1,zip_path:1,zon:5,zonif:24,zoning:[1,5,24],zoninglay:5},titles:["Referencia API","catatom2osm module","csvtools module","download module","hgwnames module","layer module","main module","CatAtom2Osm","osm module","osmxml module","setup module","test package","test.test_csvtools module","test.test_download module","test.test_hgwnames module","test.test_layer module","test.test_osm module","test.test_translate module","test.unittest_main module","translate module","Registro de cambios","Cobertura del c\u00f3digo","\u00cdndice","\u00a1Bienvenido a la documentaci\u00f3n de CatAtom2Osm!","L\u00e9eme"],titleterms:{"\u00edndic":22,advertenci:24,api:0,bienven:23,cambi:20,catatom2osm:[1,7,23],cobertur:21,codig:21,contents:11,csvtools:2,document:[23,24],downl:3,hgwnam:4,instalacion:24,lay:5,leem:24,main:6,modul:[1,2,3,4,5,6,8,9,10,11,12,13,14,15,16,17,18,19],osm:8,osmxml:9,packag:11,referent:0,registr:20,requisit:24,setup:10,submodul:11,test:[11,12,13,14,15,16,17,18],test_csvtools:12,test_downl:13,test_hgwnam:14,test_lay:15,test_osm:16,test_translat:17,translat:19,unittest_main:18,uso:24}})
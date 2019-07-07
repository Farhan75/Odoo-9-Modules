# -*- coding: utf-8 -*-
import werkzeug
from datetime import datetime
import json
import math
import base64
import logging
_logger = logging.getLogger(__name__)

import openerp.http as http
from openerp.http import request

class WebsiteDatingController(http.Controller):

    @http.route('/dating/profile/register', type="http", auth="public", website=True)
    def dating_profile_register(self, **kwargs):
        genders = request.env['res.partner.gender'].search([])
        sexual_orientations = request.env['res.sexualorientation'].search([])
        countries = request.env['res.country'].search([])
        states = request.env['res.country.state'].search([])
        cities = request.env['res.country.state.city'].search([])
        
        return http.request.render('website_dating.my_dating_register', {'genders': genders,'sexual_orientations': sexual_orientations, 'countries': countries, 'states': states, 'cities': cities} )

    @http.route('/dating/profile/register/process', type="http", auth="public", website=True, csrf=False)
    def dating_profile_register_process(self, **kwargs):
        
        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value
	    
	#Create the new user
	new_user = request.env['res.users'].sudo().create({'name': values['first_name'] + " " + values['last_name'], 'login': values['email'], 'email': values['email'], 'password': values['password'] })
	
	#Add the user to the dating group
	dating_group = request.env['ir.model.data'].sudo().get_object('website_dating', 'dating_group')
        dating_group.users = [(4, new_user.id)]

        #Remove 'Contact Creation' permission        
	contact_creation_group = request.env['ir.model.data'].sudo().get_object('base', 'group_partner_manager')
        contact_creation_group.users = [(3,new_user.id)]

        #Also remove them as an employee
	human_resources_group = request.env['ir.model.data'].sudo().get_object('base', 'group_user')
        human_resources_group.users = [(3,new_user.id)]

        #Modify the users partner record
	new_user.partner_id.write({'dating': True, 'first_name': values['first_name'], 'last_name': values['last_name'], 'gender': values['gender'], 'profile_micro': values['self_description'],'profile_visibility': 'members_only', 'sexual_orientation': values['sexual_orientation'], 'country_id': values['country'], 'state_id': values['state'], 'city_id': values['city'], 'image': base64.encodestring(values['file'].read()) })

        #Automatically sign the new user in
        request.cr.commit()     # as authenticate will use its own cursor we need to commit the current transaction
	request.session.authenticate(request.env.cr.dbname, values['email'], values['password'])

        #Redirect them to thier profile page	
        return werkzeug.utils.redirect("/dating/profiles/" + str(new_user.partner_id.id) )
        
    @http.route('/dating/profiles/like', type="http", auth="user", website=True)
    def dating_like(self, **kwargs):
        
        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value
	 
	member_id = int(values['member_id'])	
	
	like_list = http.request.env.user.partner_id.like_list
        
        #check if the partner has already liked this member
        already_liked = False
        
        if http.request.env['res.partner'].browse(member_id) in like_list:
            already_liked = True
         
        
        if already_liked == False:
            #add to like list
            http.request.env.user.partner_id.like_list = [(4, member_id)]
            
            #message the member
            message = http.request.env.user.partner_id.firstname + " likes you.\n\nClick <a href=\"/dating/profiles/" + str(http.request.env.user.partner_id.id) + "\"/>here</a> to view this members profile."
            http.request.env["res.dating.message"].sudo().create({'partner_id': http.request.env.user.partner_id.id, 'to_id': member_id, 'type': 'like', 'message':message})
    
        return werkzeug.utils.redirect("/dating/profiles/" + str(member_id) )

    @http.route('/dating/profile/update', type="http", auth="user", website=True)
    def dating_profile_update(self, **kwargs):
        
        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value
	 
	
	member_id = int(values['member_id'])
	
	#Only the owner can update there profile
	if http.request.env.user.partner_id.id != member_id:
            return "Permission Denied"
	
	member = http.request.env['res.partner'].search([('id','=',member_id), ('dating','=',True)])[0]
        
        member.profile_visibility = values['profile_visibility']
        member.message_setting = values['message_setting']
        
        
        return werkzeug.utils.redirect("/dating/profiles/" + str(member_id) )
    
    @http.route('/dating/profiles', type="http", auth="public", website=True)
    def dating_list(self, **kwargs):
    
        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value 
 
        search_list = []
        return_dict = {}
        
        #only dating members
        search_list.append(('dating','=','True'))
        
        if http.request.env.user.partner_id.name == 'Public user':
            #if not logged in only show public profiles
	    search_list.append(('profile_visibility','=','public'))                
        else:
            #if logged in they can view all non private profiles
            search_list.append(('profile_visibility','!=','not_listed'))        
        
        #min age preference
        if 'min_age' in values and values['min_age'] != '':
            search_list.append(('age','>=',values['min_age']))
            min_age = values['min_age']
        else:
            min_age = request.env.user.partner_id.min_age_pref
        
        #max age preference
        if 'max_age' in values and values['max_age'] != '':
            search_list.append(('age','<=',values['max_age']))
            max_age = values['max_age']
        else:
            max_age = request.env.user.partner_id.max_age_pref

        #gender preference
        if 'gender' in values and values['gender'] != '':
            search_list.append(('gender','=',values['gender']))
                     
        distance = ""
        if 'dist' in values and values['dist'] != '':
            distance = values['dist']
	    mylon = float(request.env.user.partner_id.longitude)
	    mylat = float(request.env.user.partner_id.latitude)
	    dist = float(values['dist']) * 0.621371
	    lon_min = mylon-dist/abs(math.cos(math.radians(mylat))*69);
	    lon_max = mylon+dist/abs(math.cos(math.radians(mylat))*69);
	    lat_min = mylat-(dist/69);
	    lat_max = mylat+(dist/69);
	            
            #Within distance
            search_list.append(('longitude','>=',lon_min))
            search_list.append(('longitude','<=',lon_max))
            search_list.append( ('latitude','<=',lat_min) )
            search_list.append( ('latitude','>=',lat_max) )
            
            
        my_dates = http.request.env['res.partner'].sudo().search(search_list, limit=15)
        my_dates_count = len(my_dates)
        
        return http.request.render('website_dating.my_dating_list', {'my_dates': my_dates, 'my_dates_count': my_dates_count, 'min_age': min_age, 'max_age': max_age, 'dist':distance} )

    @http.route('/dating/profiles/settings', type="http", auth="user", website=True)
    def dating_profile_settings(self, **kwargs):
        
        #only logged in members can view this page
        if http.request.env.user.partner_id.name != 'Public user':
            return http.request.render('website_dating.my_dating_profile_settings', {'my_date': http.request.env.user.partner_id} )
        else:
            return "Permission Denied"
 
    @http.route('/dating/profiles/messages/send', type="http", auth="user", website=True)
    def dating_profile_messages_send(self, **kwargs):

        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value 
 
        can_message = False
	        
	member_id = values['member_id']
	member = http.request.env['res.partner'].sudo().search([('id','=',values['member_id']), ('dating','=',True)])[0]
	partner = http.request.env.user.partner_id
	        
	        
	for you_likes in partner.like_list:
	    if int(member_id) == int(you_likes.id):
	        you_like = True
	        break
	            
	for they_likes in member.like_list:
	    if partner.id == they_likes.id:
	        they_like = True
	        break
	        
	#Can Message Checks
	if member.message_setting == "public":
	    can_message = True
	            
	if member.message_setting == "members_only":
	    if http.request.env.user.partner_id.name != 'Public user':
	        can_message = True
	            
	if member.message_setting == "i_like":
	    if they_like == True:
                can_message = True
 
        if can_message == True:
            in_contacts = False
            for cont in partner.contacts:
                if cont.to_id == int(member_id):
                    in_contacts = True
                    
            if in_contacts == False:
                http.request.env['res.dating.contacts'].sudo().create({'partner_id':partner.id, 'to_id': member.id})
            
            comment =  values['comment']
            
            #sender gets a copy
            http.request.env['res.dating.messages'].sudo().create({'message_owner': partner.id, 'message_partner_id': partner.id, 'message_to_id': member_id, 'message_text': comment, 'read':True})

            #recipient also gets a copy
            http.request.env['res.dating.messages'].sudo().create({'message_owner': member.id,'message_partner_id': partner.id, 'message_to_id': member_id, 'message_text': comment})

        return werkzeug.utils.redirect("/dating/profiles/" + str(member_id) )
 
    @http.route('/dating/questionnaire/<questionnaire_id>', type="http", auth="user", website=True)
    def dating_questionnaire(self, questionnaire_id, **kwargs):
        questionnaire = request.env['res.dating.questionnaire'].browse(int(questionnaire_id))
        return http.request.render('website_dating.dating_questionnaire', {'questionnaire': questionnaire} )

    @http.route('/dating/questionnaire/process', type="http", auth="user", website=True)
    def dating_questionnaire_process(self, **kwargs):

        values = {}
	for field_name, field_value in kwargs.items():
	    values[field_name] = field_value
	    
	questionnaire_id = values['questionnaire_id']
	questionnaire = request.env['res.dating.questionnaire'].sudo().browse( int(questionnaire_id) )
	
	#Currently logged in user can only submit answers for a questionnaire once
	if request.env['res.dating.questionnaire.answer'].sudo().search_count([('questionnaire_id','=',questionnaire.id), ('partner_id','=',http.request.env.user.partner_id.id) ]) > 0:
	    return "You can only answer this questionnaire once"
	
	new_questionnaire_answer = request.env['res.dating.questionnaire.answer'].sudo().create({'questionnaire_id': questionnaire.id, 'partner_id': http.request.env.user.partner_id.id})
	
	#Go through each question in this questionnaire
	for question in questionnaire.question_ids:
	    #Go through each option and determine if it was selected(prevents submitting options from other questions)
	    for option in question.option_ids:
	        if values["question_" + str(question.id)] == str(option.id):
	            request.env['res.dating.questionnaire.answer.question'].sudo().create({'questionnaire_answer_id': new_questionnaire_answer.id, 'question_id': question.id, 'option_id': option.id})
	            
	            #Only one option is allowed(prevent multi option injection)
	            break
	            
        return werkzeug.utils.redirect("/dating/questionnaire/answer/" + str(new_questionnaire_answer.id) )

    @http.route('/dating/questionnaire/answer/<questionnaire_answer_id>', type="http", auth="user", website=True)
    def dating_questionnaire_answer(self, questionnaire_answer_id, **kwargs):
	"""Perform the dating match making code"""
	
	questionnaire_answer = request.env['res.dating.questionnaire.answer'].sudo().browse( int(questionnaire_answer_id) )
	questionnaire = request.env['res.dating.questionnaire'].sudo().browse( int(questionnaire_answer.questionnaire_id.id) )

	gender_letter = ""
	if http.request.env.user.partner_id.gender.letter == "M":
	    gender_letter = "F"

	if http.request.env.user.partner_id.gender.letter == "F":
	    gender_letter = "M"
	
	output_string = ""
	candidate_list = []
	
	#First through all the answers to this questionaires which are owned by individuals of the opposite gender and are not private
	for candidate_questionnaire_answer in request.env['res.dating.questionnaire.answer'].sudo().search([('questionnaire_id','=', questionnaire.id), ('partner_id.gender.letter','=',gender_letter),('partner_id.profile_visibility','!=','not_listed') ]):
	    match_score = 0
	    skip = False
	    
	    #Go through each match rule and determine the candidate final score
	    for match_rule in questionnaire.matching_rule_ids:
	        
	        #Check if user has compare option
	        user_match_compare_option = len( request.env['res.dating.questionnaire.answer.question'].sudo().search([('questionnaire_answer_id.partner_id','=', http.request.env.user.partner_id.id), ('option_id','=', match_rule.question_compare_option_id.id)]) )
                
                #And candidate has match option
	        candidate_match_match_option = len( request.env['res.dating.questionnaire.answer.question'].sudo().search([('questionnaire_answer_id.partner_id','=', candidate_questionnaire_answer.partner_id.id), ('option_id','=', match_rule.question_match_option_id.id)]) )

                #Check if user has match option
	        user_match_match_option = len( request.env['res.dating.questionnaire.answer.question'].sudo().search([('questionnaire_answer_id.partner_id','=', http.request.env.user.partner_id.id), ('option_id','=', match_rule.question_match_option_id.id)]) )

	        #And candidate has compare option
	        candidate_match_compare_option = len( request.env['res.dating.questionnaire.answer.question'].sudo().search([('questionnaire_answer_id.partner_id','=', candidate_questionnaire_answer.partner_id.id), ('option_id','=', match_rule.question_compare_option_id.id)]) )
	        
	        if user_match_compare_option and candidate_match_match_option:
	            if match_rule.option == "match":
	                match_score += match_rule.weight
	            elif match_rule.option == "penalise":
	                match_score -= match_rule.weight
	            elif match_rule.option == "exclude":
	                skip = True
	                break
	        
	        if user_match_match_option and candidate_match_compare_option:
	            if match_rule.option == "match":
	                match_score += match_rule.weight
	            elif match_rule.option == "penalise":
	                match_score -= match_rule.weight
	            elif match_rule.option == "exclude":
	                skip = True
	                break
	                
	    #Do not add this person to the candidate list
	    if skip:
	        continue
	    else:
	        candidate_list.append( {'partner_id': candidate_questionnaire_answer.partner_id.id, 'name':candidate_questionnaire_answer.partner_id.name, 'score': match_score} )	        
	 
	candidate_list_sorted = sorted(candidate_list, key=lambda k: k['score'], reverse=True)
	
	for cand in candidate_list_sorted:
	    output_string += "<a href=\"/dating/profiles/" + str(cand["partner_id"]) + "\">" + cand["name"] + " " + str(cand["score"]) + "</a><br/>\n"
	    
	return output_string
	        
    @http.route('/dating/profiles/messages/<member_id>', type="http", auth="user", website=True)
    def dating_profile_messages(self, member_id, **kwargs):
        
        member = http.request.env['res.partner'].sudo().search([('id','=',member_id), ('dating','=',True)])[0]
        partner = http.request.env.user.partner_id
        
        #message_list = http.request.env['res.dating.messages'].search([('message_owner','=', partner.id), '|', ('message_partner_id','=', member.id), ('message_to_id','=', member.id)])
        
        message_list = http.request.env['res.dating.messages'].search([('message_owner','=', partner.id)])
        
        
        
        for mess in message_list:
            _logger.error(mess.message_text)
        
        
        #only logged in members can view this page
        if http.request.env.user.partner_id.name != 'Public user':
            return "Messages"
            #return http.request.render('website_dating.my_dating_messages', {'my_date':member, 'message_list': message_list} )
        else:
            return "Permission Denied"

            
    @http.route('/dating/profiles/<member_id>', type="http", auth="public", website=True)
    def dating_profile(self, member_id, **kwargs):
        
        you_like = False
        they_like = False
        can_view = False
        can_message = False
        
        member = http.request.env['res.partner'].sudo().search([('id','=',member_id), ('dating','=',True)])[0]
        partner = http.request.env.user.partner_id
        
        for you_likes in partner.like_list:
            if int(member_id) == int(you_likes.id):
                you_like = True
                break
            
        for they_likes in member.like_list:
            if partner.id == they_likes.id:
                they_like = True
                break
        
        #Can Message Checks
        if member.message_setting == "public":
            can_message = True
            
        if member.message_setting == "members_only":
            if http.request.env.user.partner_id.name != 'Public user':
                can_message = True
            
        if member.message_setting == "i_like":
            if they_like == True:
                can_message = True
            
        #Profile visiable checks
        if member.profile_visibility == "public":
            #everyone can view public profiles
            can_view = True
        elif member.profile_visibility == "members_only":
            #only logged in can view this profile
            if http.request.env.user.partner_id.name != 'Public user':
                can_view = True
        elif member.profile_visibility == "not_listed":
            #if this member likes you, you can view this profile
            if they_like == True:
                can_view = True
             
        #the owner can view there own profile
        if http.request.env.user.partner_id.id == int(member_id):
            can_view = True
      
        if can_view:
            questionnaires = request.env['res.dating.questionnaire'].search([])
            return http.request.render('website_dating.my_dating_profile', {'my_date': member, 'can_message': can_message, 'you_like':you_like, 'they_like':they_like, 'questionnaires': questionnaires} )
        else:
            return "Permission Denied"
# -*- coding: utf-8 -*-
import requests
from lxml import html, etree
import logging
_logger = logging.getLogger(__name__)

from openerp import api, fields, models

class WebsiteStyleManager(models.Model):

    _inherit = "website"
    
    tag_styles = fields.One2many('website.style', 'website_id', string="HTML Tag Styles")
    css_text = fields.Text(string="CSS Text")
    custom_css = fields.Text(string="Custom CSS", help="Define website wide styles and classes")
    force_styles = fields.Boolean(string="Force Styles", help="Applies an !important to all styles forcing the style over higher specificity")

    def bootsnipp_sync(self):
        #Download the featured page
        featured = "http://bootsnipp.com/snippets/featured"
        
        for i in range(1,1):
            page = requests.get(featured + "?page=" + i)
            root = html.fromstring(page.content)
            
            #Get all the snippet on the page
            snippet_list = root.xpath("//p[@class='lead snipp-title']")
            for snippet in snippet_list:
                link = html.SubElement(snippet, "a")['href']
                _logger.error(link)

    
    @api.onchange('tag_styles', 'force_styles')
    def _onchange_tag_styles(self):
        self.css_text = ""
        for style in self.tag_styles:
            self.css_text += style.html_tag.html_tag + " {\n"
            
            if style.font_family:
                self.css_text += "    font-family: '" + style.font_family.name + "'"
                if self.force_styles:
                    self.css_text += " !important"
                self.css_text += ";\n"
    
            if style.font_color:
                self.css_text += "    color: " + style.font_color
                if self.force_styles:
                    self.css_text += " !important"
                self.css_text += ";\n"

            if style.font_size:
                self.css_text += "    font-size: " + style.font_size
                if self.force_styles:
                    self.css_text += " !important"
                self.css_text += ";\n"
 
            self.css_text += "}\n\n"
    
class WebsiteStyle(models.Model):

    _name = "website.style"
    
    website_id = fields.Many2one('website', string="Website")
    html_tag = fields.Many2one('website.style.htmltag', string="HTML Tag", required=True)
    font_family = fields.Many2one('website.style.fontfamily', string="Font Family")
    font_color = fields.Char(string="Font Color", default="#000000")
    font_size = fields.Char(string="Font Size", help="The Size of the font, please include the suffix", default="16px")
    
class WebsiteStyleHTMLTag(models.Model):

    _name = "website.style.htmltag"
    
    style_id = fields.Many2one('website.style', string="Website Style")
    name = fields.Char(string="Name")
    html_tag = fields.Char(string="HTML Tag", help="Name is for fancy display 'Heading 1' this is the actual tag 'h1'")
    
class WebsiteStyleFontFamily(models.Model):

    _name = "website.style.fontfamily"
    
    style_id = fields.Many2one('website.style', string="Website Style")
    name = fields.Char(string="Font Family")
    
class WebsiteStyleFontSize(models.Model):

    _name = "website.style.fontsize"
    
    style_id = fields.Many2one('website.style', string="Website Style")
    name = fields.Char(string="Font Size", help="The Size of the font, please have em, px, % or pt suffix", default="12px")
#!/usr/bin/python
# encoding: utf-8
#
# Copyright (C) 2011 betonme
#
# In case of reuse of this source code please do not remove this copyright.
#
#	This program is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	This program is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	For more information on the GNU General Public License see:
#	<http://www.gnu.org/licenses/>.
#

import os
import struct

from Components.config import *
from Components.Element import cached
from Components.Sources.ServiceEvent import ServiceEvent as eServiceEvent
from Components.Sources.CurrentService import CurrentService as eCurrentService
from enigma import eServiceCenter, iServiceInformation, eServiceReference
from ServiceReference import ServiceReference

from CutListSupport import CutList
from MetaSupport import MetaList
from EitSupport import EitList


instance = None


class CurrentService(eCurrentService):
	def __init__(self, navcore):
		eCurrentService.__init__(self, navcore)
		self.__cutlist = None
		self.__path = None

	def cueSheet(self):
		return self.__cutlist

	@cached
	def getCurrentService(self):
		path = None
		service = self.navcore.getCurrentService()
		if service:
			if not isinstance(service, eServiceReference):
				ref = self.navcore.getCurrentlyPlayingServiceReference()
				path = ref and ref.getPath()
			else:
				path = service.getPath()
		if path and path != self.__path:
			self.__path = path
			self.__cutlist = CutList(path)
			service.cueSheet = self.cueSheet
		return service

	service = property(getCurrentService)


class ServiceEvent(eServiceEvent):
	def __init__(self):
		eServiceEvent.__init__(self)
	
	@cached
	def getInfo(self):
		return self.service and ServiceCenter.getInstance().info(self.service)
	
	info = property(getInfo)


class ServiceCenter:
	def __init__(self):
		global instance
		instance = eServiceCenter.getInstance()
		instance.info = self.info
		
	@staticmethod
	def getInstance():
		global instance
		if instance is None:
			ServiceCenter()
		return instance
		
	def info(self, service):
#		path = service.getPath()
#		from MovieCenter import extTS
#		global extTS
#		if os.path.splitext(path)[1].lower() in extTS:
#			serviceInfo = eServiceCenter.getInstance().info(service)
#			if serviceInfo is not None:
#				# Replace original cuesheet
#				serviceInfo.cueSheet = CutList(path)
#				return serviceInfo
		return ServiceInfo(service)


class ServiceInfo:
	def __init__(self, service):
		#TODO maybe necessary
		#if service and not isinstance(service, eServiceReference):
		#	if NavigationInstance and NavigationInstance.instance:
		#		service = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
		if service:
			self.service = service
			self.info = Info(service)
		else:
			self.service = None
			self.info = None
	
	def getLength(self, service):
		#TODO self.newService(service)
		return self.info and self.info.getLength() or 0
	
	def getInfoString(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sServiceref:
			return self.info and self.info.getServiceReference() or ""
		if type == iServiceInformation.sDescription:
			return self.info and self.info.getShortDescription() or ""
		if type == iServiceInformation.sTags:
			return self.info and self.info.getTags() or ""
		return "None"

	def getInfo(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sTimeCreate:
			return self.info and self.info.getMTime() or 0
		return None
	
	def getInfoObject(self, service, type):
		#self.newService(service)
		if type == iServiceInformation.sFileSize:
			return self.info and self.info.getSize() or None
		return None
	
	def getName(self, service):
		#self.newService(service)
		return self.info and self.info.getName() or ""
	
	def getEvent(self, service):
		#self.newService(service)
		return self.info


class Info:
	def __init__(self, service):
		
		# Temporary variables
		path = service and service.getPath()
		isfile = os.path.isfile(path)
		isdir = os.path.isdir(path)
		meta = path and MetaList(path)
		eit = path and EitList(path)
		
		# Information which we need later
		self.__cutlist = path and CutList(path) or []
		
		self.__size = isfile and os.stat(path).st_size \
								or isdir and config.EMC.directories_info.value and self.getFolderSize(path) \
								or None
								#TODO or isdvd
		
		self.__mtime = isfile and long(os.stat(path).st_mtime) or 0
									#TODO or isdir but show only start date
		
		self.__name = service and service.getName() or ""
		self.__servicereference = service and service.toString() or ""
		self.__servicename = ServiceReference(self.__servicereference).getServiceName() or ""
	
		self.__shortdescription = meta and meta.getMetaDescription() \
													or eit and eit.getEitShortDescription() \
													or self.__name
		self.__tags = meta and meta.getMetaTags() or ""
		
		self.__eventname = self.__name
		self.__extendeddescription = eit and eit.getEitDescription() \
																	or meta and meta.getMetaDescription() \
																	or isdir and os.path.realpath(path) \
																	or ""
		self.__id = 0
		
		#TODO remove upto ServiceInfo
		service.cueSheet = self.cueSheet

	def cueSheet(self):
		return self.__cutlist
	
	def getName(self):
		#EventName NAME
		return self.__name
	
	def getServiceReference(self):
		return self.__servicereference
	
	def getServiceName(self):
		#MovieInfo MOVIE_REC_SERVICE_NAME
		return self.__servicename
	
	def getTags(self):
		return self.__tags
	
	def getEventName(self):
		return self.__eventname
	
	def getShortDescription(self):
		#MovieInfo MOVIE_META_DESCRIPTION
		#MovieInfo SHORT_DESCRIPTION
		#EventName SHORT_DESCRIPTION
		return self.__shortdescription
	
	def getExtendedDescription(self):
		#EventName EXTENDED_DESCRIPTION
		return self.__extendeddescription
	
	def getEventId(self):
		#EventName ID
		return self.__id
	
	def getMTime(self):
		return self.__mtime
	
	def getSize(self):
		return self.__size
	
	def getLength(self):
		#self.newService(service)
		return self.__cutlist and self.__cutlist.getCutListLength() or 0
	
	def getBeginTime(self):
		self.getMTime()
	
	def getDuration(self):
		self.getLength()
	
	def getFolderSize(self, loadPath):
		folder_size = 0
		for (path, dirs, files) in os.walk(loadPath):
			for file in files:    
				filename = os.path.join(path, file)
				if os.path.exists(filename):
					folder_size += os.path.getsize(filename)
		return folder_size
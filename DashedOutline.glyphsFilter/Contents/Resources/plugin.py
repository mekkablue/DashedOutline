# encoding: utf-8

###########################################################################################################
#
#
#	Filter with dialog Plugin
#
#	Read the docs:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates/Filter%20with%20Dialog
#
#	For help on the use of Interface Builder:
#	https://github.com/schriftgestalt/GlyphsSDK/tree/master/Python%20Templates
#
#
###########################################################################################################

from __future__ import division, print_function, unicode_literals
import objc
from GlyphsApp import *
from GlyphsApp.plugins import *
from AppKit import NSPoint
from Foundation import NSClassFromString

class DashedOutline(FilterWithDialog):
	prefID = 'com.mekkablue.DashedOutline'

	# Definitions of IBOutlets
	dialog = objc.IBOutlet()
	strokeWidthField = objc.IBOutlet()
	dashField = objc.IBOutlet()
	gapField = objc.IBOutlet()
	distributeField = objc.IBOutlet()
	strokePositionField = objc.IBOutlet()

	@objc.python_method
	def settings(self):
		self.menuName = Glyphs.localize({
			'en': 'Dashed Outline',
			'de': 'Gestrichelte Kontur',
			# 'fr': 'Mon filtre',
			# 'es': 'Mi filtro',
			# 'pt': 'Meu filtro',
			# 'jp': '私のフィルター',
			# 'ko': '내 필터',
			# 'zh': '我的过滤器',
			})
		
		# Word on Run Button (default: Apply)
		self.actionButtonLabel = Glyphs.localize({
			'en': 'Apply',
			'de': 'Anwenden',
			'fr': 'Appliquer',
			'es': 'Aplicar',
			'pt': 'Aplique',
			'jp': '申し込む',
			'ko': '대다',
			'zh': '应用',
			})
		
		# Load dialog from .nib (without .extension)
		self.loadNib('IBdialog', __file__)

	# On dialog show
	@objc.python_method
	def start(self):
		
		# Set default value
		Glyphs.registerDefault(self.domain('strokeWidth'), 40.0)
		Glyphs.registerDefault(self.domain('dash'), 300.0)
		Glyphs.registerDefault(self.domain('gap'), 50.0)
		Glyphs.registerDefault(self.domain('distribute'), 0)
		Glyphs.registerDefault(self.domain('strokePosition'), 50)
		
		# Set value of text field
		self.strokeWidthField.setValue_(self.pref('strokeWidth'))
		self.dashField.setValue_(self.pref('dash'))
		self.gapField.setValue_(self.pref('gap'))
		self.distributeField.setValue_(self.pref('distribute'))
		self.strokePositionField.setValue_(self.pref('strokePosition'))
		
		# Set focus to text field
		self.strokeWidthField.becomeFirstResponder()

	@objc.python_method
	def domain(self, prefName):
		prefName = prefName.strip().strip(".")
		return self.prefID + "." + prefName.strip()

	@objc.python_method
	def pref(self, prefName):
		prefDomain = self.domain(prefName)
		return Glyphs.defaults[prefDomain]
	
	# Action triggered by UI
	@objc.IBAction
	def setStrokeWidth_(self, sender=None):
		Glyphs.defaults[self.domain('strokeWidth')] = max(1.0, sender.floatValue())
		self.update()
	
	@objc.IBAction
	def setDash_(self, sender=None):
		Glyphs.defaults[self.domain('dash')] = max(1.0, sender.floatValue())
		self.update()
	
	@objc.IBAction
	def setGap_(self, sender=None):
		Glyphs.defaults[self.domain('gap')] = max(1.0, sender.floatValue())
		self.update()

	@objc.IBAction
	def setDistribute_(self, sender=None):
		Glyphs.defaults[self.domain('distribute')] = sender.intValue()
		self.update()
	
	@objc.IBAction
	def setStrokePosition_(self, sender=None):
		Glyphs.defaults[self.domain('strokePosition')] = sender.intValue()
		self.update()
	
	@objc.python_method
	def lengthOfCurve(self, segment, precision=4):
		"""
		Returns the length of a curve segment
		"""
		innerLine = distance(segment[0], segment[3])
		outerLine = distance(segment[0], segment[1]) + distance(segment[1], segment[2]) + distance(segment[2], segment[3])
		simpleLength = (innerLine + outerLine) * 0.5
		if abs(innerLine-outerLine) < precision:
			return simpleLength
		else:
			segment1, segment2 = segment.splitAtTime_firstHalf_secondHalf_(0.5, None, None)
			return self.lengthOfCurve(segment1) + self.lengthOfCurve(segment2)
		
		length = 0
		p1 = segment[0]
		for i in range(precision):
			t = (i+1)/float(precision)
			p2 = segment.pointAtTime_(t)
			length += distance(p1, p2)
			p1 = p2
		return length
	
	@objc.python_method
	def lengthOfSegment(self, segment, precision=4):
		if len(segment) == 2:
			return segment.length()
		else:
			return self.lengthOfCurve(segment, precision=precision)
	
	@objc.python_method
	def lengthOfPath(self, path, precision=4):
		"""
		Returns length (in units) of path.
		"""
		length = 0
		for segment in path.segments:
			length += self.lengthOfSegment(segment, precision=precision)
		return length

	@objc.python_method
	def dashGapForPath(self, thisPath, dash=200, precision=4):
		"""
		Splits up thisPath into two GSPath objects:
		Returns a GSPath with the length of dash, 
		and a GSPath with the remainder of thisPath.
		"""
		dashPath = GSPath()
		dashLength = 0
		lastDashSegment, remainderSegment = None, None
		for i, thisSegment in enumerate(thisPath.segments):
			segmentLength = self.lengthOfSegment(thisSegment, precision=precision)
			if dashLength + segmentLength < dash:
				dashPath.segments = thisPath.segments[:i+1]
				dashLength += segmentLength
			else:
				if len(thisSegment) == 2:
					# straight line:
					t = (dash - dashLength) / segmentLength
					lastDashSegment, remainderSegment = thisSegment.splitAtTime_firstHalf_secondHalf_(t, None, None)
					break
				elif len(thisSegment) == 4:
					# curved segment:
					stepPrecision = 30
					for j in range(1,stepPrecision):
						t = j/stepPrecision
						lastDashSegment, remainderSegment = thisSegment.splitAtTime_firstHalf_secondHalf_(t, None, None)
						if dashLength + self.lengthOfSegment(lastDashSegment, precision=precision) >= dash:
							break
					break

		if not lastDashSegment is None and not remainderSegment is None:
			if len(dashPath.segments)==0:
				dashPath.segments = [lastDashSegment]
			else:
				dashPath.segments = dashPath.segments + [lastDashSegment]
			remainderPath = GSPath()
			remainderPath.segments = [remainderSegment] + thisPath.segments[i+1:]
			return dashPath, remainderPath
		else:
			return thisPath, None
	
	# Actual filter
	@objc.python_method
	def filter(self, layer, inEditView, customParameters):
		offsetFilter = NSClassFromString("GlyphsFilterOffsetCurve")
		roundFilter = NSClassFromString("GlyphsFilterRoundCorner")
		
		# defaults
		strokeWidth = self.pref('strokeWidth') if self.pref('strokeWidth')!=None else 40.0
		dash = self.pref('dash') if self.pref('dash')!=None else 300.0
		gap = self.pref('gap') if self.pref('gap')!=None else 50.0
		distribute = self.pref('distribute') if self.pref('distribute')!=None else 0
		strokePosition = self.pref('strokePosition') if self.pref('strokePosition')!=None else 50
		
		# Called on font export, get value from customParameters
		if "strokeWidth" in customParameters:
			strokeWidth = float(customParameters['strokeWidth'])
		if "dash" in customParameters:
			dash = float(customParameters['dash'])
		if "gap" in customParameters:
			gap = float(customParameters['gap'])
		if "distribute" in customParameters:
			distribute = int(customParameters['distribute'])
		if "strokePosition" in customParameters:
			strokePosition = int(customParameters['strokePosition'])
		
		dashLayer = layer.copyDecomposedLayer()
		dashLayer.clear()
		dashLayer.cleanUpPaths()
		dashLayer.hints = []
		workLayer = layer.copyDecomposedLayer()
		workLayer.flattenOutlines()
		workLayer.decomposeCorners()
		workLayer.removeOverlap()
		workLayer.cleanUpPaths()
		workLayer.hints = []
		
		if strokePosition != 0:
			offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
				workLayer,
				strokePosition, strokePosition, # horizontal and vertical offset
				False, # if True, creates a stroke
				False, # if True, distorts resulting shape to vertical metrics
				0, # stroke distribution to the left and right, 0.5 = middle
				None, None, None, 0, 0, True )
			
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
			dashLayer,
			strokeWidth/2, strokeWidth/2, # horizontal and vertical offset
			True, # if True, creates a stroke
			False, # if True, distorts resulting shape to vertical metrics
			strokePosition/100, # stroke distribution to the left and right, 0.5 = middle
			None, None, None, 1, 1, True )
		
		
		for path in workLayer.paths:
			dashPaths = []
			factor = 1.0
			if distribute:
				pathLength = self.lengthOfPath(path)
				howManyTimes = pathLength/(dash+gap)
				if howManyTimes > 0.9: 
					factor = howManyTimes/round(howManyTimes)
			while not path is None:
				length = (dash*factor, gap*factor)[len(dashPaths)%2]
				dashPath, path = self.dashGapForPath(path, length)
				dashPaths.append(dashPath)
			else:
				for eachPiece in dashPaths[::2]:
					# avoid small corners:
					firstSegment = eachPiece.segments[0]
					lastSegment = eachPiece.segments[-1]
					if firstSegment.type == LINE and firstSegment.length() < strokeWidth * 0.98:
						eachPiece.segments = eachPiece.segments[1:]
					if lastSegment.type == LINE and lastSegment.length() < strokeWidth * 0.98:
						eachPiece.segments = eachPiece.segments[:-1]
					# avoid path debris:
					if sum([s.length() for s in eachPiece.segments]) >= strokeWidth * 0.98:
						dashLayer.shapes.append(eachPiece)
					
		
		dashLayer.connectAllOpenPaths()
		
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
			dashLayer,
			strokeWidth/2, strokeWidth/2, # horizontal and vertical offset
			True, # if True, creates a stroke
			False, # if True, distorts resulting shape to vertical metrics
			0.5, # stroke distribution to the left and right, 0.5 = middle
			None, None, None, 1, 1, True )
			
		roundFilter.roundLayer_radius_checkSelection_visualCorrect_grid_(
			dashLayer, strokeWidth/2,
			False, # if True, only rounds user-selected points
			True, # visual correction of non-perpendicular angles
			True, # whether it the resulting path should stick to the grid
			)
		
		layer.shapes = dashLayer.shapes

	
	@objc.python_method
	def generateCustomParameter(self):
		return ("%s; strokeWidth:%i; dash:%i; gap:%i; distribute:%i; strokePosition:%i" % (
			self.__class__.__name__,
			int(self.pref("strokeWidth")),
			int(self.pref("dash")),
			int(self.pref("gap")),
			int(self.pref("distribute")),
			int(self.pref("strokePosition")),
			)).replace(".0;", ";")

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

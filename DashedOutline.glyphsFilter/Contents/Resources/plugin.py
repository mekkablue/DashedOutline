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
		
		# Set value of text field
		self.strokeWidthField.setStringValue_(self.pref('strokeWidth'))
		self.dashField.setStringValue_(self.pref('dash'))
		self.gapField.setStringValue_(self.pref('gap'))
		
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
		Glyphs.defaults[self.domain('strokeWidth')] = sender.floatValue()
		self.update()
	
	@objc.IBAction
	def setDash_(self, sender=None):
		Glyphs.defaults[self.domain('dash')] = sender.floatValue()
		self.update()
	
	@objc.IBAction
	def setGap_(self, sender=None):
		Glyphs.defaults[self.domain('gap')] = sender.floatValue()
		self.update()
	
	@objc.python_method
	def dashGapForPath(self, thisPath, dash=200, precision=20):
		"""
		Splits up thisPath into two GSPath objects:
		Returns a GSPath with the length of dash, 
		and a GSPath with the remainder after subtraction of gap.
		"""
		dashPath = GSPath()
		dashLength = 0
		lastDashSegment, remainderSegment = None, None
		for i, thisSegment in enumerate(thisPath.segments):
			segmentLength = thisSegment.length()
			if dashLength + segmentLength < dash:
				dashPath.segments = thisPath.segments[:i+1]
				dashLength += segmentLength
			else:
				if len(thisSegment) == 2:
					# straight line:
					t = (dash-dashLength)/segmentLength
					lastDashSegment, remainderSegment = thisSegment.splitAtTime_firstHalf_secondHalf_(t, None, None)
					break
				elif len( thisSegment ) == 4:
					# curved segment:
					for j in range(precision):
						t = j/precision
						lastDashSegment, remainderSegment = thisSegment.splitAtTime_firstHalf_secondHalf_(t, None, None)
						if dashLength + lastDashSegment.length() >= dash:
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
		strokeWidth = self.pref('strokeWidth')
		dash = self.pref('dash')
		gap = self.pref('gap')
		
		# Called on font export, get value from customParameters
		if "strokeWidth" in customParameters:
			strokeWidth = float(customParameters['strokeWidth'])
		if "dash" in customParameters:
			dash = float(customParameters['dash'])
		if "gap" in customParameters:
			gap = float(customParameters['gap'])
		
		dashLayer = layer.copyDecomposedLayer()
		dashLayer.clear()
		workLayer = layer.copyDecomposedLayer()
		for path in workLayer.paths:
			dashPaths = []
			while not path is None:
				length = (dash, gap)[len(dashPaths)%2]
				dashPath, path = self.dashGapForPath(path, length)
				dashPaths.append(dashPath)
			else:
				for eachPiece in dashPaths[::2]:
					if sum([s.length() for s in eachPiece.segments]) >= strokeWidth:
						# avoid path debris
						dashLayer.shapes.append(eachPiece)
		
		dashLayer.connectAllOpenPaths()
		
		offsetFilter = NSClassFromString("GlyphsFilterOffsetCurve")
		offsetFilter.offsetLayer_offsetX_offsetY_makeStroke_autoStroke_position_metrics_error_shadow_capStyleStart_capStyleEnd_keepCompatibleOutlines_(
			dashLayer,
			strokeWidth/2, strokeWidth/2, # horizontal and vertical offset
			True,     # if True, creates a stroke
			False,     # if True, distorts resulting shape to vertical metrics
			0.5,       # stroke distribution to the left and right, 0.5 = middle
			None, None, None, 1, 1, True )
			
		roundFilter = NSClassFromString("GlyphsFilterRoundCorner")
		roundFilter.roundLayer_radius_checkSelection_visualCorrect_grid_(
			dashLayer, strokeWidth/2,
			False,   # if True, only rounds user-selected points
			True, # visual correction of non-perpendicular angles
			True,       # whether it the resulting path should stick to the grid
			)
		
		layer.shapes = dashLayer.shapes

	
	@objc.python_method
	def generateCustomParameter(self):
		return "%s; strokeWidth:%s; dash:%s; gap:%s;" % (
			self.__class__.__name__,
			self.pref("strokeWidth"),
			self.pref("dash"),
			self.pref("gap"),
			)

	@objc.python_method
	def __file__(self):
		"""Please leave this method unchanged"""
		return __file__

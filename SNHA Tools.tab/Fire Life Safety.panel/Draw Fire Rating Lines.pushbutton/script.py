#   "Draw Fire Rating Lines"
#   Copyright 2022 Jared M. Holloway
#   License: MIT
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#   The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from Autodesk.Revit.DB import *
import pyrevit
from pyrevit import revit, forms

doc = pyrevit._DocsGetter().doc
selection = revit.get_selection()


def main():

	# phrase to search for in linestyle names to filter IN fire_rating_linestyles
	_FIRE_RATING_LINESTYLE_PHRASE = 'FireRating'

	# phrase to search for in linestyle names to filter IN fire_rating_linestyles by Code Requirement
	_FIRE_RATING_CODE_LINESTYLE_PHRASE = 'Code'

	# phrase to search for in linestyle names to filter IN fire_rating_linestyles by Client Request
	_FIRE_RATING_CLIENT_LINESTYLE_PHRASE = 'Client'

	# param in wall type properties to pull 'Fire Rating' value from
	# !!! must be 'Number' parameter type (aka float/double) !!!
	_FIRE_RATING_PARAM_NAME = 'Fire Rating (Hours)'

	# suffix to add to (formatted) 'Fire Rating' param value, to match linestyle name
	_FIRE_RATING_VALUE_SUFFIX = 'HR'


	fire_rating_linestyles = []
	wall_types_with_no_fire_rating = []
	view = doc.ActiveView

	# get all walls visible in the view
	walls = FilteredElementCollector(doc
			).OfCategory(BuiltInCategory.OST_Walls
			).WhereElementIsNotElementType(
			).WherePasses(VisibleInViewFilter(doc,view.Id)
			)

	# init transaction
	t = Transaction(doc,'Draw Fire Rating Lines')
	t.Start()

	# create a detail line over the top of each wall's location line;
	# set correct linestyle based on wall type's "Fire Rating" property.
	for wall in walls:

		# start a separate subtransaction before creating each detail ine
		st = SubTransaction(doc)
		st.Start()
	
	
		# get the value of the Fire Rating param from the wall's type
		wall_type = doc.GetElement(wall.GetTypeId())
		fire_rating = wall_type.LookupParameter(_FIRE_RATING_PARAM_NAME).AsDouble()
	
		# check if Fire Rating param value has been set in wall type properties
		try:
			assert fire_rating != 0
		except:
			wall_type_name = wall_type.LookupParameter('Type Name').AsString()
			if wall_type_name not in wall_types_with_no_fire_rating:
				wall_types_with_no_fire_rating.append(wall_type_name)
			st.RollBack()
			continue
	
		# format the 'Fire Rating' param value for searching linestyle names
		fire_rating_string = str(fire_rating).rstrip('0').rstrip('.') + _FIRE_RATING_VALUE_SUFFIX
	
	
		# apply different linetypes if 'Fire Rating by Client Request' inst param is checked
		if wall.LookupParameter('Fire Rating by Client Request').AsValueString() == 'Yes':
			fire_rating_type = _FIRE_RATING_CLIENT_LINESTYLE_PHRASE
		else:
			fire_rating_type = _FIRE_RATING_CODE_LINESTYLE_PHRASE
	
	
		# get the wall's location line for creating the detail line
		wall_line = wall.Location.Curve
		p0 = wall_line.GetEndPoint(0)
		p1 = wall_line.GetEndPoint(1)
		abs_line = Line.CreateBound(p0,p1)
	
		detail_line = doc.Create.NewDetailCurve(view,abs_line)
	
	
		# get the 'Fire Rating' linestyles from the project;
		# delete existing fire rating lines from view
		# should only hit this on the first iter of the loop
		if fire_rating_linestyles == []:

			linestyles = [ doc.GetElement(id)
					for id in detail_line.GetLineStyleIds()
					]
				
			fire_rating_linestyles = filter(
					lambda x: _FIRE_RATING_LINESTYLE_PHRASE in x.Name,
					linestyles
					)
		
			existing_lines_in_view = FilteredElementCollector(doc
					).OfCategory(BuiltInCategory.OST_Lines
					).WhereElementIsNotElementType(
					).WherePasses(VisibleInViewFilter(doc,doc.ActiveView.Id))
		
			existing_fire_rating_lines = filter(lambda x:
					x.LineStyle.Name in [ls.Name for ls in fire_rating_linestyles],
					existing_lines_in_view)
		
			sst = SubTransaction(doc)
			sst.Start()

			for ln in existing_fire_rating_lines:
				doc.Delete(ln.Id)

			sst.Commit()
	
	
		# pick the correct linestyle for this wall type
		# should hit this every iter of the loop (including first)
		try:
			filtered_linestyles = filter(lambda x:
					fire_rating_string in x.Name and
					fire_rating_type in x.Name,
					fire_rating_linestyles
					)
		
			# if this assignment raises an exception, list was empty (no match)
			fire_rating_linestyle = filtered_linestyles[0]
		
			# if this assertion raises an exception, there were multiple matches
			assert len(filtered_linestyles) == 1
	
		except AssertionError:
			print("ERROR:  Multiple linestyles found for '{0}' + '{1}'.".format(_FIRE_RATING_LINESTYLE_PHRASE,fire_rating_string))
			print("        Audit linestyles, then try again.\n")
			st.RollBack()
			continue
		
		except:
			print("ERROR:  No linestyles found for '{0}' + '{1}'.".format(_FIRE_RATING_LINESTYLE_PHRASE,fire_rating_string))
			print("        Audit linestyles, then try again.\n")
			st.RollBack()
			continue

		detail_line.LineStyle = fire_rating_linestyle

		# commit the per-wall subtransaction
		st.Commit()
	
	for wall_type_name in wall_types_with_no_fire_rating:
		print("WARNING:  'Fire Rating' parameter has not been set for wall type '{0}'.".format(wall_type_name))
		print("          No detail lines will be created for this wall type.\n")
	
	
	# commit the main transaction (all walls in view)
	t.Commit()


if doc.IsModified:
	forms.alert(
		msg = "This tool is still in beta testing. Please save and sync your work before using it.",
		title = "Beta Warning"
		)
else:
	main()
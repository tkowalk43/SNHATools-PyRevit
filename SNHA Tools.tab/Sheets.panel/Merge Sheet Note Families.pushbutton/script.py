#   "Merge Sheet Note Families"
#   Copyright 2022 Jared M. Holloway
#   License: MIT
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#   The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from Autodesk.Revit import *
import pyrevit
from pyrevit import revit

doc = pyrevit._DocsGetter().doc
selection = revit.get_selection()


def CoerceElementIdsToElements(func):
	import functools

	@functools.wraps(func)
	def wrapper(*args,**kwargs):
	
		args = list(args) # args comes in as a tuple, which is immutable
	
		for n,i in enumerate(args):
			if i.GetType() == DB.ElementId:
				args[n] = doc.GetElement(i)
				
		for j in kwargs:
			if kwargs[j].GetType() == DB.ElementId:
				kwargs[j] = doc.GetElement(kwargs[j])
				
		return func(*args,**kwargs)
		
	return wrapper


@CoerceElementIdsToElements
def GetParameterValue(parameter):

	if parameter.Definition.ParameterType == DB.ParameterType.Text:
		value = parameter.AsString()
	elif parameter.Definition.ParameterType == DB.ParameterType.Integer:
		value = parameter.AsInteger()
	elif parameter.Definition.ParameterType == DB.ParameterType.Number:
		value = parameter.AsDouble()
	else:
		value = parameter.AsValueString()

	return value


@CoerceElementIdsToElements
def GetSheetNoteParams(family_type):
	
	series = filter(lambda x: 'SERIES' in x.Definition.Name, family_type.Parameters)[0]
	number = filter(lambda x: 'NUMBER' in x.Definition.Name, family_type.Parameters)[0]
	text = filter(lambda x: 'TEXT' in x.Definition.Name, family_type.Parameters)[0]

	return {'series':series,'number':number,'text':text}
	

@CoerceElementIdsToElements
def DuplicateFamilyType(new_type_name, type_to_duplicate):
	
	try:
		new_family_type = type_to_duplicate.Duplicate(new_type_name)
	except Exception:
		new_type_name += '_'
		new_family_type = DuplicateFamilyType(new_type_name,type_to_duplicate)

	return new_family_type


@CoerceElementIdsToElements
def MergeSheetNoteFamilyTypes(from_family, to_family):

	GenericAnnotations = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_GenericAnnotation).WhereElementIsNotElementType()

	type_to_duplicate = list(to_family.GetFamilySymbolIds())[0]

	for from_family_type_id in list(from_family.GetFamilySymbolIds()):
		
		new_type_name = GetParameterValue(doc.GetElement(from_family_type_id).LookupParameter('Type Name'))
		new_family_type = DuplicateFamilyType(new_type_name, type_to_duplicate)

		from_params = GetSheetNoteParams(from_family_type_id).values()
		to_params = GetSheetNoteParams(new_family_type).values()

		for from_param,to_param in zip(from_params,to_params):
			to_param.Set(GetParameterValue(from_param))

		elems_to_replace = filter(lambda x: x.AnnotationSymbolType.Id == from_family_type_id, GenericAnnotations)

		for elem in elems_to_replace:
			elem.ChangeTypeId(new_family_type.Id)

	return to_family


@CoerceElementIdsToElements
def IsSheetNoteFamilyType(family_type):

	for p in family_type.Parameters:

		if 'SERIES' in p.Definition.Name:
			return True

		else:
			continue

	return False


def GetSheetNoteFamilies():

	GenericAnnontationFamilyTypes = DB.FilteredElementCollector(doc
			).OfCategory(DB.BuiltInCategory.OST_GenericAnnotation
			).WhereElementIsElementType(
			)
	SheetNoteFamilyTypes = filter(
			lambda x: IsSheetNoteFamilyType(x), GenericAnnontationFamilyTypes
			)
	SheetNoteFamilyIds = set([ family_type.Family.Id for family_type in SheetNoteFamilyTypes ])
	SheetNoteFamilies = [ doc.GetElement(family_id) for family_id in SheetNoteFamilyIds ]
	
	return SheetNoteFamilies


@CoerceElementIdsToElements
def MergeAllSheetNoteFamilyTypes():

	try:
		assert selection[0].GetType() == DB.AnnotationSymbolType
	except AssertionError:
		print("ERROR: No Generic Annotation type selected. Select (in the Project Browser) any type of the family you want to merge the other families into, the try again.")
		return None

	try:
		assert IsSheetNoteFamilyType(selection[0])
	except AssertionError:
		print("ERROR: Selected Generic Annotation type does not have a parameter with 'SERIES' in the name.")
		return None

	to_family = selection[0].Family

	for from_family in filter(lambda x: x.Id != to_family.Id, GetSheetNoteFamilies()):
		to_family = MergeSheetNoteFamilyTypes(from_family, to_family)

	return to_family


if __name__ == '__main__':

	t = DB.Transaction(doc,'Merge Sheet Note Families')
	t.Start()

	MergeAllSheetNoteFamilyTypes()

	t.Commit()

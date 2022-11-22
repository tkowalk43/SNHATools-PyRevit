#   "Change Referenced Views"
#   Copyright 2022 Jared M. Holloway
#   License: MIT
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#   The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from Autodesk.Revit import DB
import pyrevit
import pyrevit.revit
import pyrevit.forms
import pyrevit.output
from pprint import pprint

doc = pyrevit._DocsGetter().doc
selection = pyrevit.revit.get_selection()
output = pyrevit.output.get_output()

try:
    assert len(selection) == 1
    assert (
        (selection[0].GetType().BaseType == DB.View) or
        (selection[0].GetType() == DB.Viewport) or
        (selection[0].GetType() == DB.Element and selection[0].Category.Name == "Views")
        )
except:
    raise AssertionError("Selection: {0}\r\nPlease select 1 view, viewport, or reference.".format(selection[0]))
else:
    if selection[0].GetType().BaseType == DB.View:
        oldViewId = selection[0].Id
    elif selection[0].GetType() == DB.Viewport:
        oldViewId = selection[0].ViewId
    elif selection[0].GetType() == DB.Element:
        oldViewId = selection[0].get_Parameter(DB.BuiltInParameter.REFERENCED_VIEW).AsElementId()

    oldView = doc.GetElement(oldViewId)

    print("Selected view:")
    print("\t\t{0}".format(oldView.Name))

    viewers = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Viewers).WhereElementIsNotElementType()

    refs = filter(lambda x:
            (x.get_Parameter(DB.BuiltInParameter.VIEWER_IS_REFERENCE).AsInteger() == 1) and
            (x.get_Parameter(DB.BuiltInParameter.REFERENCED_VIEW).AsElementId() == oldViewId),
            viewers
            )
    
    output.next_page()
    print("References to selected view found in these views:")
    for ref in refs:
        parent_view_name = ref.get_Parameter(DB.BuiltInParameter.SECTION_PARENT_VIEW_NAME).AsValueString()
        if parent_view_name == "<none>":
            parent_view_name = str(doc.GetElement(ref.OwnerViewId).Name)
        print("\t\t{0}".format(parent_view_name))

    newView = pyrevit.forms.select_views(
            title="Select View to Reference",
            multiple=False,
            filterfunc=lambda x: x.ViewType in [DB.ViewType.DraftingView,DB.ViewType.Detail,oldView.ViewType]
            )

    if newView != None:

        output.next_page()
        print("Replacing all references to:")
        print("\t\t{0}".format(oldView.Name))
        print("with references to:")
        print("\t\t{0}".format(newView.Name))

        t = DB.Transaction(doc, "Swap View References")
        t.Start()

        for ref in refs:
            DB.ReferenceableViewUtils.ChangeReferencedView(doc,ref.Id,newView.Id)

        t.Commit()

        output.next_page()
        print("Done.")

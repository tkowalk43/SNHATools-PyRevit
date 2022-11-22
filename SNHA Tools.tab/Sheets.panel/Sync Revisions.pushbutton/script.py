#   "Sync Sheet Revisions with Sheet Issuance Parameters"
#   Copyright © 2021 Jared M. Holloway
#   License: MIT
#   Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#   The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from Autodesk.Revit import *
from rpw import revit
import re

doc = revit.doc

revision_collector = DB.FilteredElementCollector(doc).OfClass(DB.Revision).WhereElementIsNotElementType()
sheet_collector = DB.FilteredElementCollector(doc).OfClass(DB.ViewSheet).WhereElementIsNotElementType()


class Revision:
    def __init__(self, revision_element):
        self.element = revision_element
        self.id = revision_element.Id
        self.name = revision_element.Name.split(' - ')[1]
        self.regex = re.compile(self.name,re.IGNORECASE)


def SyncRevision(parameter,revision):
    sheet = parameter.Element
    rev_ids = sheet.GetAdditionalRevisionIds()

    if parameter.HasValue: # rev should be in sheet.Get...
        if revision.Id not in rev_ids:
            rev_ids.Add(revision.Id)
            sheet.SetAdditionalRevisionIds(rev_ids)
            print("{0}: {1} += {2}".format(sheet.SheetNumber,sheet.Name,revision.Name))

    else: # parameter has no value; rev should not be in sheet.Get...
        if revision.Id in rev_ids:
            rev_ids.Remove(id)
            sheet.SetAdditionalRevisionIds(rev_ids)
            print("{0}: {1} -= {2}".format(sheet.SheetNumber,sheet.Name,revision.Name))


t = DB.Transaction(doc,'Sync Revisions on Sheet with Sheet Issuance Parameters')
t.Start()

# for each revision in the project
for r in sorted(revision_collector):
    rev = Revision(r)
    
    # for each sheet in the project
    for sheet in sheet_collector:
        try:
            # get the params from the sheet whose name ~= the rev's name.
            param_list = filter(
                    lambda x: re.search(rev.regex,x.Definition.Name) != None,
                    sheet.Parameters)
            # make sure there's only 1 matching parameter.
            assert len(param_list) == 1
            # if so, that's our param. proceed to SyncRevision.
            param = param_list[0]
        # if len(param_list) != 1...
        except AssertionError:
            # if found no params matching rev name...
            if len(param_list) == 0:
                 # ...don't keep looking for it on each sheet. move on to next rev.
                break
            # if found multiple matching params...
            else:
                # ...user needs to unfuck sheet param names.
                raise Exception("Found multiple sheet parameters matching revision name \"{0}\" (case-insensitive).".format(rev.name))
        # sync.
        SyncRevision(param,rev.element)

t.Commit()
print(' ')
print('Done.')

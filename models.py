from google.appengine.ext import db
from google.appengine.ext import blobstore, search

class Account(db.Model):
    user = db.UserProperty()
    userid = db.StringProperty()
    first_name = db.StringProperty()
    last_name = db.StringProperty()
    display_name = db.StringProperty()
    phone = db.StringProperty()
    company = db.StringProperty()
    description = db.StringProperty(multiline = True)
    email = db.StringProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    points = db.IntegerProperty()
    level = db.StringProperty() #basic, advanced, super-cool etc.
    verified_info = db.BooleanProperty()
    website = db.StringProperty()
    show_completed = db.BooleanProperty()
    selected_project_title = db.StringProperty()
    selected_project_id = db.IntegerProperty()
    current_directory = db.StringProperty()
    size = db.IntegerProperty()
    size_available = db.IntegerProperty()
    showoverviewpagesidebar = db.BooleanProperty()
    showactivitypagefilterbar = db.BooleanProperty()
    editactivityimmediately = db.BooleanProperty()
    
class Project(db.Model):
    owner = db.ReferenceProperty(Account)
    title = db.StringProperty()
    description = db.TextProperty()
    show_completed = db.BooleanProperty()
    date_start = db.DateProperty()
    date_end = db.DateProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    size = db.IntegerProperty()
    status = db.TextProperty()
    #per project settings

class ProjectAccount(db.Model):
    account = db.ReferenceProperty(Account)
    project = db.ReferenceProperty(Project)
    role = db.StringProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    #permissions on a project
    editpublic = db.BooleanProperty(default = False)
    editprojectsettings = db.BooleanProperty(default = False)
    search = db.BooleanProperty(default = False)
    showspaceused = db.BooleanProperty(default = False)

    seediscussion = db.BooleanProperty(default = False)
    creatediscussion = db.BooleanProperty(default = False)
    deletecomments = db.BooleanProperty(default = False)

    seetasks = db.BooleanProperty(default = False)
    createtasks = db.BooleanProperty(default = False)
    edittasks = db.BooleanProperty(default = False)
    deletetasks = db.BooleanProperty(default = False)

    seefiles = db.BooleanProperty(default = False)
    downloadfiles = db.BooleanProperty(default = False)
    uploadfiles = db.BooleanProperty(default = False)
    deletefiles = db.BooleanProperty(default = False)
    sharefiles = db.BooleanProperty(default = False)

    seepeople = db.BooleanProperty(default = False)
    invite = db.BooleanProperty(default = False)
    editpermissions = db.BooleanProperty(default = False)
    
class Activity(search.SearchableModel):
    project = db.ReferenceProperty(Project)
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    title = db.StringProperty()
    description = db.TextProperty() #not sortable on GAE side
    responsible = db.StringProperty()
    tags = db.StringListProperty() #tags that apply, list.remove(id) upon tag del.
    date_start = db.DateProperty()
    date_due = db.DateProperty()
    date_end = db.DateProperty()
    complete = db.BooleanProperty()
    
class Filter(search.SearchableModel):
    project = db.ReferenceProperty(Project)
    account = db.ReferenceProperty(Account)
    active = db.BooleanProperty()
    filtertext = db.StringProperty()
    order = db.IntegerProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)

class Tag(db.Model):
    project = db.ReferenceProperty(Project)
    account = db.ReferenceProperty(Account) #unique per account and project
    activities = db.ListProperty(int)
    active = db.BooleanProperty()
    tagtext = db.StringProperty()
    order = db.IntegerProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)

class Event(db.Model):
    project = db.ReferenceProperty(Project)
    text = db.StringProperty()
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    referencekey = db.StringProperty()
    link = db.StringProperty()

class File(search.SearchableModel): #represents both files and folders
    account = db.ReferenceProperty(Account)
    project = db.ReferenceProperty(Project)
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    filetype = db.StringProperty()
    parentfolder = db.SelfReferenceProperty()
    name = db.StringProperty()
    description = db.StringProperty()
    data = blobstore.BlobReferenceProperty(required=False)
    flagged = db.BooleanProperty()
    size = db.IntegerProperty()

class Thread(search.SearchableModel):
    account = db.ReferenceProperty(Account)
    project = db.ReferenceProperty(Project)
    activity = db.ReferenceProperty(Activity)
    onfile = db.ReferenceProperty(File)
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
    content = db.TextProperty()
    customtitle = db.StringProperty()
    def title(self):
        if self.activity:
            return "Task: " + self.activity.title
        elif self.customtitle:
            return self.customtitle
        elif self.onfile:
            return "File " + self.onfile.name
        else:
            return "No Title"

class Comment(search.SearchableModel):
    thread = db.ReferenceProperty(Thread)
    content = db.TextProperty()
    account = db.ReferenceProperty(Account)
    date_created = db.DateTimeProperty(auto_now_add = True)
    date_edited = db.DateTimeProperty(auto_now = True)
   

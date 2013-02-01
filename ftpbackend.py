import os, datetime, random, string, urllib, math
from google.appengine.ext import webapp
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext.webapp import util
from google.appengine.dist import use_library
from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import memcache
from google.appengine.api import mail
use_library('django', '1.2')
from google.appengine.ext.webapp import template
from django.utils import simplejson
from models import *
#import braintree

SENDER = "outgoing@followtheproject.com"

URLS = {
    'main': '/',
    'account': '/account',
    'newproject': '/newproject',
    'editproject': '/editproject/', ##  {{URLS.editproject}}{{project.key.id}}
    'overview': '/project/{{ project.key.id }}/overview', #change to discussion?
    'tasks':  '/project/{{ project.key.id }}/tasks',
    'thread': '/discussion/', ##{{ URLS.thread }}{{ thread.key.id }}
    'filters': '/project/{{ project.key.id }}/filters',
    'search': '/project/{{ project.ket.id }}/search',
    'removefilter': '/removefilter/', ## {{URLS.removefilte}}{{filter.key.id}}
    'removetag': '/removetag/',
    'toggletagfilter': '/toggletagfilter/',
    'task': '/task/',  ## {{URLS.task}}{{activity.key.id}}
    'nopermission': '/permission',   ## nopermission?a=Create Tasks
    'ajaxactivitycomment': '/ajax/activitycomment/',  #+ activity.key.id
    'ajaxactivityaddtag': '/ajax/activityaddtag/',  #+ activity.key.id
    'ajaxactivitytoggle': '/ajax/activitytoggle/', #+ activity id and tag id
    'ajaxactivitytagdelete': '/ajax/activitytagdelete/', #+ activity id and tag id
    'templates': '_templates/',
    'css': '/_static/',
    'static': '/_static/',
    'js': '/_static/_js/',
    }

def render(self, t, values):
    values['URLS'] = URLS
    try: values['referer'] = self.request.headers['Referer']
    except: values['referer'] = "/"
    values['account'] = Account.all().filter("user =", values['user']).get()
    templatefile = URLS['templates'] + t
    path = os.path.join(os.path.dirname(__file__), templatefile)
    self.response.out.write(template.render(path, values))

def nopermission(param = ""):
    path = URLS['nopermission'] + "?a=" + param
    return path

class AccountPage(webapp.RequestHandler):
    def get(self):
        subpagecode = self.request.get('p')
        subpage = "projects"
        if subpagecode == "ui":
            subpage = "userinformation"
        elif subpagecode == "us":
            subpage = "usersettings"
        user = users.get_current_user()
        account = Account.all().filter("user = ", user).get()
        projects = Project.all().filter("owner =", account).run()
        messagetext = self.request.get("m")
        values = {
            'selected': 'account',
            'subpage': subpage,
            'user': user,
            'messagetext': messagetext,
            'login_url': users.create_login_url('/logincheck?r=account'),
            'logout_url': users.create_logout_url('/'),
            'projects': projects,
            }
        render(self, 'account.html', values)
    def post(self): #accountpage post
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()

        account.display_name = self.request.get("display_name")
        account.first_name = self.request.get("first_name")
        account.last_name = self.request.get("last_name")
        account.email = self.request.get("email")
        account.company = self.request.get("company")
        account.description = self.request.get("description")
        account.website = self.request.get("website")
        account.phone = self.request.get("phone")

        if not account.verified_info:
            account.verified_info = True
        account.put()
        self.redirect(URLS['account'])

class ActivityListPage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        #project = Project.get_by_id(account.selected_project_id))
        try: project = Project.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        if not user or not project.owner.user == user:
            self.redirect(URLS['main'])
        account.selected_project_title = project.title
        account.selected_project_id = project.key().id()
        account.put()
        activities = project.activity_set
        if not account.show_completed:
            activities.filter("complete !=", True).order("complete")
        #sort activities
        if self.request.get("s"):
            sortedby = self.request.get("s")
        else:
            sortedby = None
        if sortedby == "task":
            activities.order("title")
        elif sortedby == "-task":
            activities.order("-title")
        elif sortedby == "due":
            activities.order("date_due")
        elif sortedby == "-due":
            activities.order("-date_due")
        elif sortedby == "complete":
            activities.order("date_end")
        elif sortedby == "-complete":
            activities.order("-date_end")
        elif sortedby == "responsible":
            activities.order("responsible")
        elif sortedby == "-responsible":
            activities.order("-responsible")
        else:
            sortedby = None

        tags = account.tag_set.filter("project =", project)
        #list of lists of tags for the project & account
        activetags = [t for t in tags if t.active]
        #list of ids of activities to include
        if activetags: 
            filteredactivityids = activetags[0].activities
            for i in activetags[1:]:
                for t in filteredactivityids:
                #remove any activities that are not shared among all active tags
                    if t not in i.activities:
                        filteredactivityids.remove(t)
        #remove duplicates
            filteredactivityids = list(set(filteredactivityids))
        #final list of included activities, in the preserved sorted order
            filteredactivities = []
            for a in activities:
                if a.key().id() in filteredactivityids:
                    filteredactivities.append(a)
        else:
            filteredactivities = activities

        values = {
            'project': project,
            'activities': filteredactivities,
            'selected': 'tasks',
            'user': user,
            'sortedby': sortedby,
            'tags': tags,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'activitylistpage.html', values)
    def post(self, id): #activitylistpage post
        action = self.request.get('action')
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        try: project = Project.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not user or not project.owner.user == user:
            self.redirect(URLS['main'])
        if action == "newactivity":
            if not projectaccount.createtasks:
                return self.redirect(nopermission("Create Tasks"))
            activity = Activity(
                project = project,
                title = self.request.get('title'),
                description = None,
                date_start = datetime.date.today(),
                date_due = None,
                date_end = None,
                responsible = "",
                complete = False,
                )
            if activity.title == "": activity.title = "None"
            activity.put()
            tags = Tag.all().filter("project =", project).filter("account =", account)
            for tag in tags:
                if tag.active:
                    tag.activities.append(activity.key().id())
                    tag.put()
        if action == "newtag":
            #activities are the same is the AND set of all theh other active tags
            tags = Tag.all().filter("project =", project).filter("account =", account)
            activetags = [t for t in tags if t.active]

            if activetags:
                filteredactivityids = activetags[0].activities
                for i in activetags[1:]:
                    for t in filteredactivityids:
                #remove any activities that are not shared among all active tags
                        if t not in i.activities:
                            filteredactivityids.remove(t)
            else:
                filteredactivityids = []

            tag = Tag(
                project = project,
                account = account,
                tagtext = self.request.get("tagtext"),
                active = True,
                activities = filteredactivityids,
                )
            tag.put()
        if action == "showhidecompleted":
            if account.show_completed:
                account.show_completed = False
            else:
                account.show_completed = True
            account.put()

        self.redirect('/project/' + str(project.key().id()) + '/tasks')

class ActivityPage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        activity = Activity.get_by_id(int(id))
        tags = account.tag_set.filter("project =", activity.project)
        values = {
            'user': user,
            'activity': activity,
            'project': activity.project,
            'selected': 'tasks',
            'login_url': users.create_login_url('/logincheck?r=account'),
            'logout_url': users.create_logout_url('/'),
            'tags': tags,
            }
        render(self, 'activitypage.html', values)
    def post(self, id): #activitypage
        activity = Activity.get_by_id(int(id))
        projectid = str(activity.project.key().id())
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(projectid))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.edittasks: 
            return self.redirect(nopermission("Edit Tasks"))
        if self.request.get("delete") == "on":
            if not projectaccount.deletetasks:
                return self.redirect(nopermission("Delete Tasks"))
            activity.delete()
            return self.redirect("/project/" + projectid + "/tasks")
        activity.title = self.request.get("title")
        activity.description = self.request.get("description")
        if self.request.get("date_start") != "":
            activity.date_start = datetime.datetime.strptime(self.request.get("date_start"), "%m/%d/%Y").date()
        else:
            activity.date_start = None
        if self.request.get("date_due") != "":
            activity.date_due = datetime.datetime.strptime(self.request.get("date_due"), "%m/%d/%Y").date()
        else:
            activity.date_due = None
        if self.request.get("date_end") != "":
        #if date complete was blank before, mark activity as complete
            if activity.date_end == None or activity.date_end == "":
                activity.complete = True
            activity.date_end = datetime.datetime.strptime(self.request.get("date_end"), "%m/%d/%Y").date()
        else:
            activity.date_end = None
        activity.responsible = self.request.get("responsible")
        if self.request.get("complete") == "on":
            activity.complete = True
        else:
            activity.complete = False
        activity.put()
        self.redirect("/project/" + str(activity.project.key().id()) + "/tasks")

class ActivityComment(webapp.RequestHandler):
    def post(self, activityid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        try: activity = Activity.get_by_id(int(activityid))
        except: activity = None
        if not projectaccount.seediscussion:
            return self.redirect(nopermission("View Discussion"))
        #get thread or create new thread if one does not exist already
        thread = Thread.all().filter("activity =", activity).get()
        if not thread:
            thread = Thread(
                activity = activity,
                project = project,
                account = account,
                )
            thread.put()
        #create the comment
        comment = Comment(
            thread = thread,
            account = account,
            content = self.request.get("commentinput")
            )
        comment.put()
        self.redirect("/task/" + str(activity.key().id()))

class FilesPage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.seefiles:
            return self.redirect(nopermission("View Files"))
        if not user:
            return self.redirect('/')
        try: current_directory = temp = File.get_by_id(int(account.current_directory))
        except: current_directory = temp = None
        folder_breadcrumb = []
        while temp is not None:
            if temp.filetype == "folder": folder_breadcrumb.insert(0, temp)
            if temp.parentfolder: temp = temp.parentfolder
            else: temp = None

        #reverse the order of the breadcrump
        #folder_breadcrumb.reverse()

        if current_directory == None:    #root
            folders = project.file_set.filter("filetype =", "folder").filter("parentfolder =", None).run()
            files = project.file_set.filter("filetype = ", "file").filter("parentfolder =", None).run()
        elif current_directory.filetype == 'folder':  #folder
            folders = current_directory.file_set.filter("filetype =", "folder").run()
            files = current_directory.file_set.filter("filetype =", "file").run()
        elif current_directory.filetype == 'file':    #file
            pass
        
        upload_url = blobstore.create_upload_url("/upload/" + str(project.key().id()))
        if projectaccount.showspaceused:
            storagepercent = int(100 * project.owner.size / project.owner.size_available)
        else:
            storagepercent = None
        values = {
            'user': user,
            'project': project,
            'folder_breadcrumb': folder_breadcrumb,
            'selected': 'files',
            'folders': folders,
            'files': files,
            'upload_url': upload_url,
            'storagepercent': storagepercent,
            }
        render(self, "filespage.html", values)
    def post(self, id):
        pass

class FileSetDirectory(webapp.RequestHandler):
    def get(self, id, directory):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        
        if directory == "root":
            account.current_directory = None
        else:
            account.current_directory = directory
        account.put()
        self.redirect("/project/" + str(project.key().id()) + "/files")

#handlers for upload file, new folder, delete file/folder

class UploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, projectid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(projectid))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.uploadfiles:
            return self.redirect(nopermission("Create Files"))
        upload_files = self.get_uploads('uploadfile')
        blob_info = upload_files[0]
        if (account.size_available - account.size) < blob_info.size:
            #redirect, the project does not have space for the new file
            blob_info.delete()
            return self.redirect("/account")
        f = File(
            account = account,
            project = project,
            filetype = "file",
            name = blob_info.filename,
            data = blob_info,
            size = blob_info.size,
            )
        try: current_directory = File.get_by_id(int(account.current_directory))
        except: current_directory = None
        if current_directory:
            f.parentfolder = current_directory
        else:
            f.parentfolder = None
        f.put()
        #calc size of all parent folders
        f = f.parentfolder
        while f is not None:
            f.size = sum([i.size for i in f.file_set])
            f.put()
            f = f.parentfolder
        project.size = sum([i.size for i in project.file_set.filter("parentfolder =", None).run()])
        project.put()
        account.size = sum([i.size for i in account.project_set])
        account.put()
        self.redirect("/project/" + str(project.key().id()) + "/files")

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, fileid):
        f = File.get_by_id(int(fileid))
        user = users.get_current_user()
        account = Account.all().filter("user =" ,user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.downloadfiles:
            return self.redirect(nopermission("Download Files"))
        blob_info = blobstore.BlobInfo.get(f.data.key())
        self.send_blob(blob_info)

class FileNewFolder(webapp.RequestHandler):
    def post(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.uploadfiles:
            return self.redirect(nopermissoin("Create Files"))
        folder = File(
            project = project,
            filetype = 'folder',
            name = self.request.get("foldername"),
            size = 0,
            )
        try: current_directory = File.get_by_id(int(account.current_directory))
        except: current_directory = None
        if current_directory:
            folder.parentfolder = current_directory
        else:
            folder.parentfolder = None
        folder.put()        
        self.redirect("/project/" + str(project.key().id()) + "/files")

class LoginCheck(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        #no account found. check for email address changes in google account
        if not account:
            account = Account.all().filter("userid =", user.user_id()).get()
            if account:
                account.user = user
        #create a new account
        if not account:
            account = Account(
                user = user,
                userid = user.user_id(),
                verified_info = False,
                email = user.email(),
                show_completed = False,
                size = 0,
                size_available = 500000,
                #any other starting info
                )
        account.selected_project_title = None
        account.selected_project_id = None
        account.current_directory = None
        account.put()
        if not account.verified_info:
#redirect them to the verify info page, same as the account info page.
            return self.redirect(URLS['account'] + "?p=ui")
        if self.request.get('r'):
            return self.redirect(URLS['main'] + str(self.request.get('r')))
        else:
            self.redirect(URLS['main'])

class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user: 
            account = Account.all().filter("user =", user).get()
        else: 
            account = None
        if account:
            project = Project.get_by_id(int(account.selected_project_id))
        else:
            project = None
        values = {
            'selected': 'main',
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/logincheck?r=account'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'main.html', values)

class EditProject(webapp.RequestHandler):
    def get(self, id=None):
        if id:
            try: project = Project.get_by_id(int(id))
            except: pass
        else:
            project = None
        values = {
            'selected': 'account',
            'user': users.get_current_user(),
            'project': project,
            'today': datetime.date.today(),
            'login_url': users.create_login_url('/logincheck?r=account'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'newproject.html', values)
    def post(self, id=None):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if not id: #new project, create it and also create a projectaccount
            project = Project(
                title = self.request.get("projectTitle"),
                description = self.request.get("projectDescription"),
                status = self.request.get("projectStatus"),
                owner = account, #owner = Account NOT user
                show_completed = False,
                date_start = datetime.date.today(),
                )
            project.put()
            projectaccount = ProjectAccount(
                project = project,
                account = account,
                role = "Master Account",
                seediscussion = True,
                creatediscussion = True,
                deletecomments = True,
                uploadfiles = True,
                downloadfiles = True,
                deletefiles = True,
                sharefiles = True,
                invite = True,
                createtasks = True,
                edittasks = True,
                deletetasks = True,
                seetasks = True,
                seepeople = True,
                editpublic = True,
                seefiles = True,
                editprojectsettings = True,
                search = True,
                editpermissions = True,
                showspaceused = True,
                )
            projectaccount.put()
        else:
            project = Project.get_by_id(int(id))
            projectaccount = project.projectaccount_set.filter("account =", account).get()
            if not projectaccount.editprojectsettings:
                return self.redirect(nopermission("Edit Project Settings"))
            project.title = self.request.get("projectTitle")

            if self.request.get("date_start") != "":
                project.date_start = datetime.datetime.strptime(self.request.get("date_start"), "%m/%d/%Y").date()
            else:
                project.date_start = None
            if self.request.get("date_end") != "":
                project.date_end = datetime.datetime.strptime(self.request.get("date_end"), "%m/%d/%Y").date()
            else:
                project.date_end = None
            project.status = self.request.get("projectStatus")
            project.description = self.request.get("projectDescription")
            project.put()
        
        self.redirect(self.request.get('referer'))

class FilterPage(webapp.RequestHandler):
    def get(self, id):
        project = Project.get_by_id(int(id))
        filters = project.filter_set
        user = users.get_current_user()
        values = {
            'selected': 'tasks',
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            'filters': filters,
            'project': project,
            }
        render(self, 'filterpage.html', values)
    def post(self, id):
        project = Project.get_by_id(int(id))
        filters = project.filter_set
        if self.request.get('action') == "newfilter":
            newfilter = Filter(
                active = True,
                project = project, ##TIE TO ACCOUNT + PROJECT, LOAD BY ACCOUNT and PROJECT
                account = Account.all().filter("user =", users.get_current_user()).get(),
                filtertext = self.request.get("filtertext"),
                )
            newfilter.put()
        self.redirect('/project/' + str(project.key().id()) + '/tasks')

class OverviewPage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        try: project = Project.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        account.selected_project_title = project.title
        account.selected_project_id = project.key().id()
        account.current_directory = None
        account.put()
        if not projectaccount.seediscussion:
            threads = None
        else:
            threads = project.thread_set.order("-date_edited")
        values = {
            'project': project,
            'selected': 'overview',
            'threads': threads,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'overviewpage.html', values)
    def post(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        try: project = Project.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.creatediscussion:
            return self.redirect(nopermission("Participate in Discussion"))
        if self.request.get("action") == "newthread":
            t = Thread(
                account = account,
                project = project,
                customtitle = self.request.get("threadname")
                )
            t.put()
        self.redirect("/project/" + str(project.key().id()) + "/overview")

class RemoveTag(webapp.RequestHandler):
    def get(self, id):
        try: t = Tag.get_by_id(int(id))
        except: pass
        #check that the user and project are correct
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if t.project.key().id() == account.selected_project_id:
            t.delete()
        self.redirect("/project/" + str(account.selected_project_id) + "/tasks")
        
class ToggleTagFilter(webapp.RequestHandler):
    def get(self, id):
        try: t = Tag.get_by_id(int(id))
        except: pass
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if t:
            t.active = not t.active
        t.put()
        self.redirect("/project/" + str(account.selected_project_id) + "/tasks")

class RemoveFilter(webapp.RequestHandler):
    def get(self, id):
        try: f = Filter.get_by_id(int(id))
        except: pass
        #check that the user and project are correct
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if f.project.key().id() == account.selected_project_id:
            f.delete()
        self.redirect("/project/" + str(account.selected_project_id) + "/tasks")

class ToggleFilter(webapp.RequestHandler):
    def get(self, id):
        try: f = Filter.get_by_id(int(id))
        except: pass
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if f:
            f.active = not f.active
        f.put()
        self.redirect("/project/" + str(account.selected_project_id) + "/tasks")

class SearchPage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.search:
            return self.redirect(nopermission("Search"))
        searchquery = self.request.get("q")
        activities = Activity.all().filter("project =", project).search(searchquery)
        threads = Thread.all().filter("project =", project).search(searchquery)
        files = File.all().filter("project =", project).search(searchquery)
        comments = Comment.all().filter("project =", project).search(searchquery)
        results = {
            'activities': activities,
            'files': files,
            'threads': threads,
            'comments': comments,
            }
        if searchquery in [""]:
            results = None
        values = {
            'selected': 'search',
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            'results': results,
            'searchquery': searchquery,
            }
        render(self, 'searchpage.html', values)
    def post(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.search:
            return self.redirect(nopermission("Search"))
        searchquery = self.request.get("q")
        activities = Activity.all().filter("project =", project).search(searchquery)
        threads = Thread.all().filter("project =", project).search(searchquery)
        files = File.all().filter("project =", project).search(searchquery)
        comments = Comment.all().filter("project =", project).search(searchquery)
        results = {
            'activities': activities,
            'threads': threads,
            'comments': comments,
            'files': files,
            }
        values = {
            'selected': 'search',
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            'results': results,
            'searchquery': searchquery,
            }
        render(self, 'searchpage.html', values)

class PeoplePage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.seepeople:
            return self.redirect(nopermission("See People"))
        people = ProjectAccount.all().filter("project =", project)
        if self.request.get("i"):
            message = "Invitation sent to " + self.request.get("i")
        else:
            message = None
        values = {
            'selected': 'people',
            'project': project,
            'user': user,
            'people': people,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            'message': message,
            }
        render(self, 'peoplepage.html', values)        
    def post(self, projectid, personid):
        #person delete etc
        self.redirect("/project/" + str(projectid) + "/people")
            
class InvitePage(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.invite:
            return self.redirect(nopermission("Invite People"))
        values = {
            'selected': 'people',
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'newuserpage.html', values)        
    def post(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.invite:
            return self.redirect(nopermission("Invite People"))
        newaccount = Account(
            first_name = self.request.get("firstname"),
            last_name = self.request.get("lastname"),
            display_name = self.request.get("firstname") + " " + self.request.get("lastname"),
            email = self.request.get("email"),
            )
        newaccount.put()
        newprojectaccount = ProjectAccount(
            project = project,
            account = newaccount,
            role = self.request.get("role"),
            )
        if self.request.get("editpublic") == "on": newprojectaccount.editpublic = True
        if self.request.get("editprojectsettings") == "on": newprojectaccount.editprojectsettings = True
        if self.request.get("search") == "on": newprojectaccount.search = True
        if self.request.get("showspaceused") == "on": newprojectaccount.showspaceused = True
        #if self.request.get("discussion") == "notvisible": newprojectaccount.
        if self.request.get("discussion") == "visible": newprojectaccount.seediscussion = True
        if self.request.get("discussion") == "participate": newprojectaccount.creatediscussion = True
        if self.request.get("discussion") == "admin": newprojectaccount.detecomments = True
        #if self.request.get("tasks") == "notvisible": newprojectaccount.
        if self.request.get("tasks") == "visible": newprojectaccount.seetasks = True
        if self.request.get("tasks") == "create": newprojectaccount.createtasks = True
        if self.request.get("tasks") == "edit": newprojectaccount.edittasks = True
        if self.request.get("tasks") == "delete": newprojectaccount.deletetasks = True
        if self.request.get("seefiles") == "on": newprojectaccount.seefiles = True
        if self.request.get("downloadfiles") == "on": newprojectaccount.downloadfiles = True
        if self.request.get("uploadfiles") == "on": newprojectaccount.uploadfiles = True
        if self.request.get("deletefiles") == "on": newprojectaccount.deletefiles = True
        if self.request.get("sharefiles") == "on": newprojectaccount.sharefiles = True
        if self.request.get("seepeople") == "on": newprojectaccount.seepeople = True
        if self.request.get("invite") == "on": newprojectaccount.invite = True
        if self.request.get("editpermissions") == "on": newprojectaccount.editpermissions = True

        newprojectaccount.put()
        #send an email to the invitee
        if mail.is_email_valid(newaccount.email):
            confirmationlink = "http://www.followtheproject.com/accept/" + str(newaccount.key().id())
            sender = SENDER
            subject = "Invitation to Collaborate on" + newprojectaccount.project.title
            body = """
You have been invited by %s to collaborate on a project at FollowtheProject.com! Please accept this invitation by clicking on the link below:
%s
""" % (account.email, confirmationlink)
            html = """<p>You have been invited by %s to collaborate on a project at FollowtheProject.com! Please accept this invitation by clicking on the link below:<p>
<a href="%s">Confirm</a>
""" % (account.email, confirmationlink)
            message = mail.EmailMessage(
                sender = sender,
                subject = subject,
                to = newaccount.email,
                body = body,
                html = html,
                )
            message.send()
            #i is used on peoplepage to display an invitation message
            self.redirect('/project/' + str(project.key().id()) + '/people?i=' + newaccount.display_name)
        else:
            values = {
                'selected': 'people',
                'project': project,
                'user': user,
                'login_url': users.create_login_url('/'),
                'logout_url': users.create_logout_url('/'),
                'firstname': newaccount.first_name,
                'lasname': newaccount.last_name,
                'email': newaccount.email,
                'message': "Please enter a valid email address",
                }
            render(self, 'newuserpage.html', values)        

class AcceptInvitation(webapp.RequestHandler):
    def get(self, accountid):
        '''accountid is the id of the account generated at invite creation
        several cases to handle:
        1. person has no account
        2. person has account and is NOT logged in
        3. person has an account and logged in '''
        user = users.get_current_user()
        if user:
            account = Account.all().filter("user =", user).get()
        invitedaccount = Account.get_by_id(int(accountid))
        projectaccount = ProjectAccount.all().filter("account =", invitedaccount).get()
        #confirm before assigning projectaccount to existing account? yes move this to a POST section. only applicable if account exists, just assign the project account and remove the invitedaccount.
        if account:
            projectaccount.account = account
            projectaccount.put()
            invitedaccount.delete()
        #person has no account, or is not logged in, will be redirected.
        if not user:
            login_url = users.create_login_url('/accept/' + str(accountid))
            self.redirect(login_url)
        values = {
            'user': user,
            'account': account,
            'invitedaccount': invitedaccount,
            'logout_url': users.create_logout_url('/')
            }
        render(self, 'accept.html', values)
    def post(self, accountid):
        pass
   
class OverviewDiscussion(webapp.RequestHandler):
    def get(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        try: thread = Thread.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        project = thread.project
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.seediscussion:
            self.redirect(nopermission("View Discussion"))
        values = {
            'thread': thread,
            'selected': 'overview',
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            }
        render(self, 'overview_discussion.html', values)
    def post(self, id):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        try: thread = Thread.get_by_id(int(id))
        except:
            self.redirect(URLS['main'])
        project = thread.project
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.creatediscussion:
            return self.redirect(nopermission("Participate in Discussion"))
        comment = Comment(
            thread = thread,
            account = account,
            content = self.request.get('commentinput')
            )
        comment.put()
        thread.put()
        self.redirect(URLS['thread'] + str(thread.key().id()))

def deletefolder(folder):
    pass

def deletefile(f):
    pass

class DeleteFiles(webapp.RequestHandler):
    def post(self, projectid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(projectid))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.deletefiles:
            return self.redirect(nopermission("Delete Files"))
        fileids = self.request.get('fileids').split(",")
        fileids = [int(i) for i in fileids]
        #should always contain a zero in front. the get_by_id will fail with it in.
        if 0 in fileids:
            fileids.remove(0)
        self.response.out.write(fileids)
        folder = File.get_by_id(fileids[0]).parentfolder
        for f in fileids:
            f = File.get_by_id(int(f))
            if f.filetype == "folder":
                pass#deletefolder(f)
            if f.filetype == "file":
                blobstore.delete(f.data.key())
                f.delete()
        #calc folder, project, account sizes
        while folder is not None:
            folder.size = sum([i.size for i in folder.file_set])
            folder.put()
            folder = folder.parentfolder
        project.size = sum([i.size for i in project.file_set.filter("parentfolder =", None).run()])
        project.put()
        account.size = sum([i.size for i in account.project_set])
        account.put()
        #return filesids
        #self.response.out.write(fileids);
        self.redirect("/project/" + str(project.key().id()) + "/files")

class NoPermission(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        requestedaction = self.request.get('a')
        project = Project.get_by_id(account.selected_project_id)
        values = {
            'project': project,
            'user': user,
            'login_url': users.create_login_url('/'),
            'logout_url': users.create_logout_url('/'),
            'project': project,
            'requestedaction': requestedaction,
            'referer': self.request.get('referer'),
            }
        render(self, 'nopermission.html', values)

#### AJAX HANDLERS (these do not always render return content)
class AjaxToggleFilterBar(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        if account.showactivitypagefilterbar:
            account.showactivitypagefilterbar = False
        else:
            account.showactivitypagefilterbar = True
        account.put()

class AjaxActivityAddNewTag(webapp.RequestHandler):
    def post(self, activityid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        try: activity = Activity.get_by_id(int(activityid))
        except: activity = None
        tag = Tag(
            activities = [activity.key().id()],
            project = project,
            account = account,
            active = False,
            tagtext = self.request.get("tagtext")
            )
        tag.put()
        values = {
            'tags': Tag.all().filter("account =", account).filter("project =", project),
            'activity': activity,
            }
        t = '/_ajax/activitytags.html'
        templatefile = URLS['templates'] + t
        path = os.path.join(os.path.dirname(__file__), templatefile)
        self.response.out.write(template.render(path, values))

class AjaxActivityComment(webapp.RequestHandler):
    def post(self, activityid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        projectaccount = project.projectaccount_set.filter("account =", account).get()
        if not projectaccount.creatediscussion:
            return self.redirect(nopermission("Participate in Discussion"))
        try: activity = Activity.get_by_id(int(activityid))
        except: activity = None
        #get thread or create new thread if one does not exist already
        thread = Thread.all().filter("activity =", activity).get()
        if not thread:
            thread = Thread(
                activity = activity,
                project = project,
                account = account,
                )
        #save new thread, and update existing ones
        thread.put()
        #create the comment
        comment = Comment(
            thread = thread,
            account = account,
            content = self.request.get("commentinput")
            )
        comment.put()
        values = {
            'comments': activity.thread_set[0].comment_set
            }
        t = '/_ajax/activitycomment.html'
        templatefile = URLS['templates'] + t
        path = os.path.join(os.path.dirname(__file__), templatefile)
        self.response.out.write(template.render(path, values))

class AjaxActivityToggle(webapp.RequestHandler): #toggle tag on activity page
    def post(self, activityid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        try: activity = Activity.get_by_id(int(activityid))
        except: activity = None
        try: tag = Tag.get_by_id(int(self.request.get("tagid")))
        except: tag = None
        if activity.key().id() in tag.activities:
            tag.activities.remove(activity.key().id())
        else:
            tag.activities.append(activity.key().id())
        tag.put()
        values = {
            'tags': Tag.all().filter("account =", account).filter("project =", project),
            'activity': activity,
            }
        t = '/_ajax/activitytags.html'
        templatefile = URLS['templates'] + t
        path = os.path.join(os.path.dirname(__file__), templatefile)
        self.response.out.write(template.render(path, values))

class AjaxActivityTagDelete(webapp.RequestHandler):
    def post(self, activityid):
        user = users.get_current_user()
        account = Account.all().filter("user =", user).get()
        project = Project.get_by_id(int(account.selected_project_id))
        try: activity = Activity.get_by_id(int(activityid))
        except: activity = None
        try: tag = Tag.get_by_id(int(self.request.get("tagid")))
        except: tag = None
        tag.delete()
        values = {
            'tags': Tag.all().filter("account =", account).filter("project =", project),
            'activity': activity,
            }
        t = '/_ajax/activitytags.html'
        templatefile = URLS['templates'] + t
        path = os.path.join(os.path.dirname(__file__), templatefile)
        self.response.out.write(template.render(path, values))

def main():
    application = webapp.WSGIApplication([
            ('/account', AccountPage),
            ('/ajax/tfb', AjaxToggleFilterBar),
            (r'/ajax/activitycomment/(.*)', AjaxActivityComment),
            (r'/ajax/activityaddtag/(.*)', AjaxActivityAddNewTag),
            (r'/ajax/activitytoggle/(.*)', AjaxActivityToggle),
            (r'/ajax/activitytagdelete/(.*)', AjaxActivityTagDelete),
            (r'/editproject/(.*)', EditProject),
            ('/permission', NoPermission),
            (r'/project/(.*)/files', FilesPage),
            (r'/project/(.*)/files/delete', DeleteFiles),
            (r'/project/(.*)/files/(.*)', FileSetDirectory),
            (r'/project/(.*)/newfolder', FileNewFolder),
            (r'/project/(.*)/search', SearchPage),
            (r'/project/(.*)/people', PeoplePage),
            (r'/project/(.*)/invite', InvitePage),
            (r'/accept/(.*)', AcceptInvitation),
            (r'/project/(.*)/overview', OverviewPage),
            (r'/project/(.*)/tasks', ActivityListPage),
            ('/logincheck', LoginCheck),
            ('/newproject', EditProject),
            (r'/removetag/(.*)', RemoveTag),
            (r'/toggletagfilter/(.*)', ToggleTagFilter),
            (r'/serve/(.*)', ServeHandler),
            (r'/task/(.*)', ActivityPage),
            (r'/taskcomment/(.*)', ActivityComment),
            (r'/discussion/(.*)', OverviewDiscussion),
            (r'/upload/(.*)', UploadHandler),
            ('/', MainPage),
            ],debug=True)

    util.run_wsgi_app(application)

if __name__ == '__main__':
    main()

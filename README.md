# AO3 API

This is an unofficial API that let's you access some of AO3's (archiveofourown.org) data through Python.

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install AO3 API.

```bash
pip install ao3_api
```

## Github

https://github.com/ArmindoFlores/ao3_api


## Usage

There are 3 types of classes added by the API: ```AO3.Work```, ```AO3.User``` and ```AO3.Session```


You can use the ```AO3.Work``` class to pull data from a work stored in archiveofourown.org

```python
>>> import AO3
>>> work = AO3.Work(14392692) # 14392692 is the workid
>>> work.title
'The Roots That Clutch'
>>> work.date_published
datetime.date(2018, 4, 22)
>>> work.authors
['laquearia']
>>> work.language
'English'
>>> 
```

You can get the chapter text by calling ```work.load_chapters()``` followed by ```work.get_chapter_text(chapter)```

```python
>>> import AO3
>>> work = AO3.Work(14392692)
>>> work.load_chapters()
>>> text = work.get_chapter_text(1)
>>> print(' '.join(text.split(' ')[:20]))  # Print the first 20 words

Chapter Text
It all starts with a suggestion.“Hey, we should make this a thing,” Midoriya says one day, out of the
>>> 
```

If you don't call ```work.load_chapters()``` you might get this error:
```python
Traceback (most recent call last):
  File "<pyshell#9>", line 1, in <module>
    work.get_chapter_text(1)
  File "C:\Python36\lib\site-packages\AO3\works.py", line 27, in get_chapter_text
    raise utils.UnloadedError("Work.load_chapters() must be called first")
AO3.utils.UnloadedError: Work.load_chapters() must be called first
```

You can use the ```AO3.User``` class to pull data from a user profile:

```python
>>> import AO3
>>> user = AO3.User("laquearia")
>>> user.url
'https://archiveofourown.org/users/laquearia'
>>> print(user.bio)
I have no idea what I'm doing, but I know I'm doing it very, very well.  (Artist, 23, in love with tea. Check out my shit.)NOTE: I am known for my angst. Read my things with caution and a box of tissues.
>>>  user.works  # Number of works published
11
>>>
```

Use ```user.get_work_list(page)``` to get all the works in a page from the user. If you're not sure how many pages there are, use ```user.npages```


If you have an archiveofourown.org account, you can login with using ```AO3.session(username, password)``` and get a session to access that that's only accessible when you're logged in.

```python
>>> import AO3
>>> sess = AO3.session("myusername", "mypassword")
>>> sess.get_n_bookmarks()
10
>>> sess.get_bookmarks(page=1)  # Get all bookmarks in a page in the format (id, 'work title', ['author1', 'author2'])
[(123456, 'Work Title', ['author1'])]
>>> sess.get_subscriptions(page=1) # Get all subscriptions in a page in the format (id, 'work title', ['author1', 'author2'])
[(123456, 'Work Title', ['author1'])]
>>>
```

If you provide a wrong username / password this error will be raised:

```python
Traceback (most recent call last):
  File "<pyshell#11>", line 1, in <module>
    s = AO3.Session("as", "as")
  File "C:\Python36\lib\site-packages\AO3\session.py", line 20, in __init__
    raise utils.LoginError("Invalid username or password")
AO3.utils.LoginError: Invalid username or password
```

```AO3.utils.workid_from_url(url)``` is a functions that returns the workid given a work url:

```python
>>> import AO3
>>> AO3.utils.workid_from_url("https://archiveofourown.org/works/14392692/chapters/33236241")
14392692
>>> AO3.utils.workid_from_url("https://archiveofourown.org/works/14392692")
14392692
>>> AO3.utils.workid_from_url("works/14392692/chapters/33236241")
14392692
>>>
```

## Future functionalities

In the future, if no official API is released, I might add a search option and more session options (subscribe to works, kudos and comment).


## Contact info

For information or bug reports please contact francisco.rodrigues0908@gmail.com.


## License
[MIT](https://choosealicense.com/licenses/mit/)
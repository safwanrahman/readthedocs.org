import requests
from django.contrib.auth.models import User
from requests import ConnectionError

from readthedocs.core.utils import trigger_build
from readthedocs.projects.models import Project

base_url = "http://readthedocs.org/api/v2/project/"
COUNT = 0


def create_project(repo, name, repo_type):
    user = User.objects.all().get(username="safwan")
    try:
        p = Project.objects.create(repo=repo, name=name, repo_type=repo_type)
        trigger_build(p, basic=True)
        p.users.add(user)
        print(u"successfully created {}".format(p.name))
        return p.id
    except Exception:
        print("unsuccessful", name)


def fetch(url=None, all_projects=[]):
    url = url or base_url
    resp = requests.get(url)
    data = resp.json()
    results = data['results']

    for project in results:
        canonical_url = project['canonical_url']
        try:
            p = Project.objects.all().filter(name=project['name'])
            if not p.exists():
                req = requests.get(canonical_url)
                if req.status_code == 200 and project['documentation_type'] == "sphinx":
                    p = create_project(repo=project['repo'], name=project['name'],
                                       repo_type=project['repo_type'])
                    if p:
                        all_projects.append(p)

                    if len(all_projects) == 10000:
                        print("Successufl")
                        return None
        except ConnectionError:
            pass

    next_url = data['next']
    fetch(url=next_url)


fetch(url=base_url)

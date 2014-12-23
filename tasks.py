from invoke import run, task


@task
def test():
    run('nosetests --with-coverage --cover-package twittercide')

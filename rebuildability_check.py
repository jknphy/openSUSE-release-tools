#!/usr/bin/python3

import argparse
import logging
import sys

import osc.core
import osc.conf

import osclib.remote_project
from osclib.remote_project import RemoteProject
import osclib.dependencies

class RebuildabilityChecker(object):
    def __init__(self, project_str, triggered_by_str):
        self.logger = logging.getLogger('RebuildibilityChecker')
        self.project = RemoteProject.find(project_str) # apiurl should be read from osc.conf.config['apiurl'], osclib config class looks like has different goal?
        self.triggered_by = triggered_by_str
        if self.triggered_by:
            self.triggered_by = self.triggered_by.split(",")

    def result(self):
        packages = self.project.get_packages(inherited = True) # package should include also project from which it comes. Recursive means include also inherited packages so reading meta and linked projects are needed
        self.logger.debug("Packages %s" % [pkg.project_name + " -> " + pkg.name for pkg in packages])

        if self.triggered_by:
            package_names = [pkg.name for pkg in packages]
            triggered_packages = list(filter(lambda pkg: pkg.name in self.triggered_by, packages))
            # filter packages to include only ones affected by triggered packages
            packages = osclib.Dependencies.compute_depends_on(triggered_packages, packages)

        title = "Testing rebuild of whole parent project"
        description = "Temporary project including expanded copy of parent to verify if everything can be rebuild from scratch"
        rebuild_project = self.project.create_subproject("Rebuild", title, description) # how to handle if it exists? Clean it and use? What if we do not have permission to create subproject?

        testing_packages = [package.link(rebuild_project.name) for package in packages]
        while not all([p.builds.is_finished for p in testing_packages]): # builds is object for handling building and is_finished means that all builds are finished ( or disabled )
            # write some progress about number of pass, failures, what is waiting, etc. using p.builds query ( ensure it is not memoized )
            print("Working like a crazy monk")

        # TODO: delete rebuild project or keep it for inspection?
        return all([not p.builds.any_failed for p in testing_packages])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Do testing rebuild of packages including inherited ones')
    parser.add_argument('-p', '--project', type=str, default='openSUSE:Factory',
                        help='project to check (ex. openSUSE:Factory, openSUSE:Leap:15.1)')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug information')
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-t', '--triggered_by', default=None,
        help='Comma separated list of packages that trigger rebuild check. '
            'Without it full rebuild is done.')

    args = parser.parse_args()

    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    rebuild_report = RebuildabilityChecker(args.project, args.triggered_by)

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.debug("All linked projects: %s" % [p.name for p in rebuild_report.project.metadata.linked_projects(recursive = True)])

    result = rebuild_report.result()

    # TODO: maybe print some final report?

    if not result:
        # Maybe print packages ( including project source ) that failed
        sys.exit(1)

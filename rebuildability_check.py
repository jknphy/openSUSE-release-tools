#!/usr/bin/python3

import argparse
import logging
import sys

import osc.core
import osc.conf

import osclib.remote_project
from osclib.remote_project import RemoteProject
import osclib.dependency

class RebuildabilityChecker(object):
    def __init__(self, project_str, packages, repository, dry_run):
        self.logger = logging.getLogger('RebuildibilityChecker')
        self.project = RemoteProject.find(project_str) # apiurl should be read from osc.conf.config['apiurl'], osclib config class looks like has different goal?
        self.packages = packages
        self.repository = repository
        self.dry_run = dry_run

    def result(self):
        packages = self.project.get_packages()
        self.logger.debug("Packages %s" % ["%s / %s" % (p.source_project_name(), p.name) for p in packages])

        if self.packages:
            package_names = [pkg.name for pkg in packages]
            # filter packages to include only ones affected by triggered packages
            filtered_packages = list(filter(lambda pkg: pkg.name in self.packages, packages))
            if self.repository:
                packages = osclib.dependency.Dependency.compute_rebuilds(filtered_packages, packages, repository=self.repository)
            else:
                packages = filtered_packages

        if self.dry_run:
            for pkg in packages:
                print(pkg.name)

            return True

        title = "Testing rebuild of whole parent project"
        description = "Temporary project including expanded copy of parent to verify if everything can be rebuild from scratch"
        rebuild_project = self.project.create_subproject("Rebuild", title, description) # how to handle if it exists? Clean it and use? What if we do not have permission to create subproject?

        testing_packages = [package.link(rebuild_project.name) for package in packages]

        self.logger.info("Rebuild project '%s' created." % rebuild_project.name)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Do testing rebuild of packages including inherited ones')
    parser.add_argument('-p', '--project', type=str, default='openSUSE:Factory',
                        help='project to check (ex. openSUSE:Factory, openSUSE:Leap:15.1)')
    parser.add_argument('-d', '--debug', action='store_true', default=False,
                        help='enable debug information')
    parser.add_argument('-A', '--apiurl', metavar='URL', help='API URL')
    parser.add_argument('-P', '--packages', default=None,
        help='Comma separated list of packages to rebuild. '
            'Without it full rebuild of all packages in project is done.')
    parser.add_argument('-f', '--packages-file', default=None,
        help='Same as --packages, just list of packages are read from file. '
            'Format is one package per line.')
    parser.add_argument('-n', '--dependencies', default=None,
        help='Use together with --packages to add also dependencies of given packages in the repository.'
            'Example "--packages=glibc --dependencies=openSUSE_Factory --project=Staging:A".')
    parser.add_argument('-D', '--dry-run', action='store_true',
        help='Do not create rebuild project and just print out list of packages to rebuild.')

    args = parser.parse_args()

    osc.conf.get_config(override_apiurl=args.apiurl)
    osc.conf.config['debug'] = args.debug

    packages = None
    if args.packages:
        packages = args.packages.split(",")
    if not packages and args.packages_file:
        file = open(args.packages_file, "r")
        packages = [l.strip() for l in file.readlines()]

    rebuild_report = RebuildabilityChecker(args.project, packages, args.dependencies, args.dry_run)

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

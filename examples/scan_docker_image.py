'''
Created on Apr 11, 2019

@author: kumykov

Docker image layer by layer scan.

This program will download docker image and scan it into Blackduck server layer by layer
Each layer will be scanned as a separate project
Then all layers will be added to an umbrella project as components
This will allow the layers to be reported as part of the whole container or alone.

For a standard container image specification as in

      repository/image-name:version

Main project will be named "repository/image-name" and will have "version" as a version

Docker Inspector scan project on squashed imaged will be named as "repository/image-name"_squashed and will have "version" as a version

Sub-projects for layers will be named as
      repository/image-name_layer_1
      repository/image-name_layer_2
      .........

Usage:

scan_docker_image.py [-h] [--cleanup CLEANUP] imagespec

positional arguments:
  imagespec          Container image tag, e.g. repository/imagename:version

optional arguments:
  -h, --help         show this help message and exit
  --cleanup CLEANUP  Delete project hierarchy only. Do not scan
  
  --rescan-layer  NUM  Rescans specific layer. No project structure cleanup will be performed

'''

from blackduck.HubRestApi import HubInstance
from pprint import pprint
from sys import argv
import json
import os
import requests
import shutil
import subprocess
import sys
from argparse import ArgumentParser
import argparse

#hub = HubInstance()

'''
quick and dirty wrapper to process some docker functionality
'''
class DockerWrapper():
   
    def __init__(self, workdir, scratch = True):
        self.workdir = workdir
        self.imagedir = self.workdir + "/container"
        self.imagefile = self.workdir + "/image.tar"
        if scratch:
            self.initdir()
        self.docker_path = self.locate_docker()
        
    def initdir(self):
        if os.path.exists(self.workdir):
            if os.path.isdir(self.workdir):
                shutil.rmtree(self.workdir)
            else:
                os.remove(self.workdir)
        os.makedirs(self.workdir, 0o755, True)
        os.makedirs(self.workdir + "/container", 0o755, True)

        
    def locate_docker(self):
        os.environ['PATH'] += os.pathsep + '/usr/local/bin'
        args = []
        args.append('/usr/bin/which')
        args.append('docker')
        proc = subprocess.Popen(['which','docker'], stdout=subprocess.PIPE)
        out, err = proc.communicate()
        lines = out.decode().split('\n')
        print(lines)
        if 'docker' in lines[0]:
            return lines[0]
        else:
            raise Exception('Can not find docker executable in PATH.')
        
    def pull_container_image(self, image_name):
        args = []
        args.append(self.docker_path)
        args.append('pull')
        args.append(image_name)
        return subprocess.run(args)
        
    def save_container_image(self, image_name):
        args = []
        args.append(self.docker_path)
        args.append('save')
        args.append('-o')
        args.append(self.imagefile)
        args.append(image_name)
        return subprocess.run(args)
    
    def unravel_container(self):
        args = []
        args.append('tar')
        args.append('xvf')
        args.append(self.imagefile)
        args.append('-C')
        args.append(self.imagedir)
        return subprocess.run(args)
    
    def read_manifest(self):
        filename = self.imagedir + "/manifest.json"
        with open(filename) as fp:
            data = json.load(fp)
        return data
        
    def read_config(self):
        manifest = self.read_manifest()
        configFile = self.imagedir + "/" + manifest[0]['Config']
        with open(configFile) as fp:
            data = json.load(fp)
        return data
 
class Detector():
    def __init__(self, hub):
        # self.detecturl = 'https://blackducksoftware.github.io/hub-detect/hub-detect.sh'
        self.detecturl = 'https://detect.synopsys.com/detect.sh'
        self.baseurl = hub.config['baseurl']
        self.filename = '/tmp/hub-detect.sh'
        self.token=hub.config['api_token']
        self.baseurl=hub.config['baseurl']
        self.download_detect()
        
    def download_detect(self):
        with open(self.filename, "wb") as file:
            response = requests.get(self.detecturl)
            file.write(response.content)

    def detect_run(self, options=['--help']):
        cmd = ['bash']
        cmd.append(self.filename)
        cmd.append('--blackduck.url=%s' % self.baseurl)
        cmd.append('--blackduck.api.token=' + self.token)
        cmd.append('--blackduck.trust.cert=true')
        cmd.extend(options)
        subprocess.run(cmd)

    def detect_inspector_run(self, options=['--help']):
        cmd = ['bash']
        cmd.append(self.filename)
        cmd.append('--blackduck.url=%s' % self.baseurl)
        cmd.append('--blackduck.api.token=' + self.token)
        cmd.append('--blackduck.trust.cert=true')
        cmd.append('--detect.tools=DOCKER')
        #cmd.append('--detect.docker.inspector.air.gap.path=/root/packaged-inspectors/docker')
        cmd.extend(options)
        subprocess.run(cmd)


class ContainerImageScanner():
    
    def __init__(self, hub, container_image_name, workdir='/tmp/workdir', dockerfile=None, base_image=None, omit_base_layers=False):
        self.hub = hub
        self.hub_detect = Detector(hub)
        self.docker = DockerWrapper(workdir)
        self.container_image_name = container_image_name
        cindex = container_image_name.rfind(':')
        if cindex == -1:
            self.image_name = container_image_name
            self.image_version = 'latest'
        else:
            self.image_name = container_image_name[:cindex]
            self.image_version = container_image_name[cindex+1:]
        self.dockerfile = dockerfile
        self.base_image = base_image
        self.omit_base_layers = omit_base_layers
        
    def prepare_container_image(self):
        self.docker.initdir()
        self.docker.pull_container_image(self.container_image_name)
        self.docker.save_container_image(self.container_image_name)
        self.docker.unravel_container()

    def process_container_image(self):
        self.manifest = self.docker.read_manifest()
        print(self.manifest)
        self.config = self.docker.read_config()
        print (json.dumps(self.config, indent=4))
        
        self.layers = []
        num = 1
        offset = 0
        for i in self.manifest[0]['Layers']:
            layer = {}
            layer['name'] = self.image_name + "_layer_" + str(num)
            layer['path'] = i
            while self.config['history'][num + offset -1].get('empty_layer', False):
                offset = offset + 1
            layer['command'] = self.config['history'][num + offset - 1]
            layer['shaid'] = self.config['rootfs']['diff_ids'][num - 1]
            self.layers.append(layer)
            num = num + 1
        print (json.dumps(self.layers, indent=4))

    def generate_project_structures(self, base_layers=None):
        main_project_release = self.hub.get_or_create_project_version(self.image_name, self.image_version)

        for layer in self.layers:
            parameters = {}
            parameters['description'] = layer['command']['created_by']
            sub_project_release = self.hub.get_or_create_project_version(layer['name'], self.image_version, parameters=parameters)
            self.hub.add_version_as_component(main_project_release, sub_project_release)
        # Process base and add-on parts
        if base_layers:
            base_image_version = self.image_version + "__base_layers"
            addon_image_version = self.image_version + "_addon_layers"
            base = []
            addon = []
            
            for layer in self.layers:
                if layer['shaid'] in base_layers:
                    base.append(layer)
                else:
                    addon.append(layer)
            
            print ("Number of base layers {}".format(len(base)))
            print ("Number of addon layers {}".format(len(addon))) 
            
            if (len(base) > 0):
                main_project_release_addon = self.hub.get_or_create_project_version(self.image_name, addon_image_version)
                if not self.omit_base_layers:
                    main_project_release_base = self.hub.get_or_create_project_version(self.image_name, base_image_version)
                    for layer in base:
                        parameters = {'description': layer['command']['created_by']}
                        sub_project_release = self.hub.get_or_create_project_version(layer['name'], self.image_version, parameters=parameters)
                        self.hub.add_version_as_component(main_project_release_base, sub_project_release)
                for layer in addon:
                    parameters = {'description': layer['command']['created_by']}
                    sub_project_release = self.hub.get_or_create_project_version(layer['name'], self.image_version, parameters=parameters)
                    self.hub.add_version_as_component(main_project_release_addon, sub_project_release)
            else:
                print("************************************************************")
                print("*                                                          *")
                print("* No layers from Dockerfile/base  are present in the image *")
                print("*                                                          *")
                print("************************************************************")
            
    def generate_single_layer_project_structure(self, layer_number):
        main_project_release = self.hub.get_or_create_project_version(self.image_name, self.image_version)

        layer = self.layers[layer_number - 1]
        parameters = {}
        parameters['description'] = layer['command']['created_by']
        sub_project_release = self.hub.get_or_create_project_version(layer['name'], self.image_version, parameters=parameters)
        self.hub.add_version_as_component(main_project_release, sub_project_release)

    def submit_layer_scans(self):
        for layer in self.layers:
            options = []
            options.append('--detect.project.name={}'.format(layer['name']))
            options.append('--detect.project.version.name="{}"'.format(self.image_version))
            # options.append('--detect.blackduck.signature.scanner.disabled=false')
            options.append('--detect.code.location.name={}_{}_code_{}'.format(layer['name'],self.image_version,layer['path']))
            options.append('--detect.source.path={}/{}'.format(self.docker.imagedir, layer['path'].split('/')[0]))
            self.hub_detect.detect_run(options)

    def submit_single_layer_scan(self, layer_number):
        layer = self.layers[layer_number-1]
        options = []
        options.append('--detect.project.name={}'.format(layer['name']))
        options.append('--detect.project.version.name="{}"'.format(self.image_version))
        # options.append('--detect.blackduck.signature.scanner.disabled=false')
        options.append('--detect.code.location.name={}_{}_code_{}'.format(layer['name'],self.image_version,layer['path']))
        options.append('--detect.source.path={}/{}'.format(self.docker.imagedir, layer['path'].split('/')[0]))
        self.hub_detect.detect_run(options)

    def submit_docker_inspector_scan(self):
        main_project_release = self.hub.get_or_create_project_version(self.image_name, self.image_version)
        sub_project_release = self.hub.get_or_create_project_version(self.image_name + "_squashed", self.image_version)
        self.hub.add_version_as_component(main_project_release, sub_project_release)
        options = ['--detect.project.name={}_squashed'.format(self.image_name),
                   '--detect.project.version.name="{}"'.format(self.image_version),
                   '--detect.code.location.name=DI_{}'.format(self.docker.imagefile),
                   '--detect.docker.tar={}'.format(self.docker.imagefile)]
        self.hub_detect.detect_inspector_run(options)

    def cleanup_project_structure(self):
        release = self.hub.get_or_create_project_version(self.image_name,self.image_version)
        base_release = self.hub.get_project_version_by_name(self.image_name,self.image_version + "__base_layers")
        addon_release = self.hub.get_project_version_by_name(self.image_name,self.image_version + "_addon_layers")
        squahed_release = self.hub.get_project_version_by_name(self.image_name,self.image_version + "_squashed")
        
        print("--------")
        print(base_release)
                    
        components = self.hub.get_version_components(release)
        
        print (components)
        
        for item in components['items']:
            sub_name = item['componentName']
            sub_version_name = item['componentVersionName']
            sub_release = self.hub.get_or_create_project_version(sub_name, sub_version_name)
            print(self.hub.remove_version_as_component(release, sub_release))
            if base_release:
                print(self.hub.remove_version_as_component(base_release, sub_release))
            if addon_release:
                print(self.hub.remove_version_as_component(addon_release, sub_release))
        
            project = self.hub.get_project_by_name(sub_name)
            versions = self.hub.get_project_versions(project)
            if versions['totalCount'] == 1:
                print(self.hub.delete_project_by_name(sub_name))
            else:
                print(self.hub.delete_project_version_by_name(sub_name, sub_version_name))
        
        if base_release:
            print(self.hub.delete_project_version_by_name(self.image_name,self.image_version + "__base_layers"))
        if addon_release:
            print(self.hub.delete_project_version_by_name(self.image_name,self.image_version + "_addon_layers"))
        if squahed_release :
            print(self.hub.delete_project_version_by_name(self.image_name, self.image_version + "_squashed"))
        project = self.hub.get_project_by_name(self.image_name)
        versions = self.hub.get_project_versions(project)
        if versions['totalCount'] == 1:
            print(self.hub.delete_project_by_name(self.image_name))
        else:
            print(self.hub.delete_project_version_by_name(self.image_name,self.image_version))
        
    def get_base_layers(self):
        if (not self.dockerfile)and (not self.base_image):
            raise Exception ("No dockerfile or base image specified")
        imagelist = []
        
        if self.dockerfile:
            from pathlib import Path
            dfile = Path(self.dockerfile)
            if not dfile.exists():
                raise Exception ("Dockerfile {} does not exist",format(self.dockerfile))
            if not dfile.is_file():
                raise Exception ("{} is not a file".format(self.dockerfile))
            with open(dfile) as f:
                for line in f:
                    if 'FROM' in line.upper():
                        a = line.split()
                        if a[0].upper() == 'FROM':
                            imagelist.append(a[1])                    
        if self.base_image:
            imagelist.append(self.base_image)
        
        print (imagelist)
        base_layers = []
        for image in imagelist:
            self.docker.initdir()
            self.docker.pull_container_image(image)
            self.docker.save_container_image(image)
            self.docker.unravel_container()
            manifest = self.docker.read_manifest()
            print(manifest)
            config = self.docker.read_config()
            print(config)
            base_layers.extend(config['rootfs']['diff_ids'])
        return base_layers  
    

def scan_container_image(imagespec, layer_number=0):
    
    hub = HubInstance()
    scanner = ContainerImageScanner(hub, imagespec)
    scanner.prepare_container_image()
    scanner.process_container_image()
    if layer_number == 0:
        scanner.generate_project_structures()
        scanner.submit_layer_scans()
    else:
        scanner.generate_single_layer_project_structure(layer_number)
        scanner.submit_single_layer_scan(int(layer_number))


def scan_squashed_image(imagespec) :
    hub = HubInstance()
    scanner = ContainerImageScanner(hub, imagespec)
    scanner.prepare_container_image()
    scanner.submit_docker_inspector_scan()


def scan_container_image_with_dockerfile(imagespec, dockerfile, base_image, omit_base_layers):
    hub = HubInstance()
    scanner = ContainerImageScanner(hub, imagespec, dockerfile=dockerfile, base_image=base_image, omit_base_layers=omit_base_layers)
    base_layers = scanner.get_base_layers()
    print (json.dumps(base_layers, indent=2))
    # sys.exit()
    scanner.prepare_container_image()
    scanner.process_container_image()
    scanner.generate_project_structures(base_layers)
    scanner.submit_layer_scans()


def clean_container_project(imagespec):
    hub = HubInstance()
    scanner = ContainerImageScanner(hub, imagespec)
    scanner.cleanup_project_structure()


def main(argv=None):
    
    if argv is None:
        argv = sys.argv
    else:
        argv.extend(sys.argv)
        
    parser = ArgumentParser()
    parser.add_argument('imagespec', help="Container image tag, e.g.  repository/imagename:version")
    parser.add_argument('--inspector', default=False, help="Runs Docker Inspector scan on squashed image")
    parser.add_argument('--cleanup', default=False, help="Delete project hierarchy only. Do not scan")
    parser.add_argument('--rescan-layer',default=0, type=int, help="Rescan specific layer in case of failure, 0 - scan as usual")
    parser.add_argument('--dockerfile',default=None, type=str, help="Specify dockerfile used to build this container(experimantal), can't use with --base-image")
    parser.add_argument('--base-image',default=None, type=str, help="Specify base image used to build this container(experimantal), can't use with --dockerfile")
    parser.add_argument('--omit-base-layers',default=False, type=bool, help="Omit base layer (requires --dockerfile or --base-image)")
    args = parser.parse_args()
    
    print (args);

    if not args.imagespec:
        parser.print_help(sys.stdout)
        sys.exit(1)

    if args.dockerfile and args.base_image:
        parser.print_help(sys.stdout)
        sys.exit(1)
            
    if args.omit_base_layers and not (args.dockerfile or args.base_image):
        parser.print_help(sys.stdout)
        sys.exit(1)
    
    if args.cleanup:
        clean_container_project(args.imagespec)
        sys.exit(1)
    if args.dockerfile or args.base_image:
        clean_container_project(args.imagespec)
        scan_container_image_with_dockerfile(args.imagespec, args.dockerfile, args.base_image, args.omit_base_layers)
    else:
        if args.rescan_layer == 0:
            clean_container_project(args.imagespec)
            scan_container_image(args.imagespec)
        else:
            scan_container_image(args.imagespec, args.rescan_layer)
    if args.inspector :
            scan_squashed_image(args.imagespec)

if __name__ == "__main__":
    sys.exit(main())

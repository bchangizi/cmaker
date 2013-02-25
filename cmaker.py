#!/usr/bin/python

import re, urllib2, zipfile, tarfile
import os, sys, subprocess, platform, shutil, hashlib, argparse

parser = argparse.ArgumentParser()
parser.add_argument("src_path", default=".")
parser.add_argument("--cm_flags", default="")
parser.add_argument("--cm_initial_cache", default="")
parser.add_argument("--verbose", action="count", default=0)

args= parser.parse_args()

verbosity_level = args.verbose
cmake_flags = args.cm_flags 
cmake_initial_cache = args.cm_initial_cache 

print cmake_flags
print cmake_initial_cache
print "Verbosity level", verbosity_level 

src_path    = os.path.abspath(args.src_path)
tmp_dir     = os.path.abspath(os.path.join(".", os.path.basename(src_path) + "-" + hashlib.md5(src_path).hexdigest()[:2]))
work_dir    = os.path.join(tmp_dir, "cm")
build_dir   = os.path.join(work_dir, "build")
stage_dir   = os.path.join(work_dir, "stage")
deploy_dir  = tmp_dir


target_os_names     = ["Windows", "Linux", "Darwin"]
target_march_names  = ["x86", "x64"]
target_config_names = ["Debug", "Release"]

cmake_locations = { 'Windows' : "c:/Program Files (x86)/CMake 2.8/bin/cmake.exe" ,
                    'Linux'   : "/usr/bin/cmake" , 
                    'Darwin'  : "/usr/bin/cmake" }
generator_names = { 'Windows' : {'x86' : 'Visual Studio 10', 'x64' : 'Visual Studio 10 Win64'},
                    'Linux'   : {'x86' : 'Unix Makefiles'  , 'x64' : 'Unix Makefiles'        },
                    'Darwin'  : {'x86' : 'Unix Makefiles'  , 'x64' : 'Unix Makefiles'        }  }

uname = platform.uname()
cur_os_name = uname[0]
cpu_name = uname[4]

def main():
    cmake = cmake_locations[cur_os_name]
    
    shutil.rmtree("include", True)
    shutil.rmtree("lib", True)

    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    global src_path
    if src_path.startswith("http://") == True:
        remotefile = urllib2.urlopen(src_path)
        url = remotefile.geturl()
        basename = os.path.basename(url)
        filename = os.path.join(work_dir, basename)

        if not os.path.exists(filename):
            print "Downloading", url
            with open(filename, "wb") as file:
                file.write(remotefile.read())

            print "Extracting", filename
            extract_if_needed(filename, work_dir)

        src_path = os.path.join(work_dir, re.split(".tar.bz2|.tar.gz|.zip", os.path.basename(filename))[0])

    for target_os_name in target_os_names:
        for march in target_march_names:
            for config in target_config_names:
                generator = generator_names[target_os_name][march]
                specific_suffix = "-" + target_os_name + "-" + march + "-" + config
                specific_build_dir = build_dir + specific_suffix
                specific_stage_dir = stage_dir + specific_suffix
            
                # could add cross compile here
                if target_os_name != cur_os_name:
                    continue

                if not os.path.exists(specific_stage_dir):
                    if not os.path.exists(specific_build_dir):
                        os.makedirs(specific_build_dir)

                    build = [cmake, "-G", generator]
		    if len(cmake_initial_cache) > 0: build += ["-C", cmake_initial_cache]
		    if len(cmake_flags) > 0: build += cmake_flags.split() 
                    build += ["-DCMAKE_INSTALL_PREFIX=" + specific_stage_dir] 
                    build += [src_path]
                    stage = [cmake, "--build", specific_build_dir, "--config", config, "--target", "install"]

                    subprocess.call(build, cwd=specific_build_dir)
                    subprocess.call(stage, cwd=specific_build_dir)
 
                # assuming the includes are the same for all builds
                if not os.path.exists(os.path.join(deploy_dir, "include")):
                    shutil.copytree(os.path.join(specific_stage_dir, "include"), os.path.join(deploy_dir, "include"))
                
                shutil.copytree(os.path.join(specific_stage_dir, "lib"), 
                                os.path.join(os.path.join(deploy_dir, "lib"), target_os_name, march, config))

def extract_if_needed(path, targetdir):
    if not os.path.exists(targetdir):
        os.makedirs(targetdir)

    if path.endswith('.zip'):
        opener, mode = zipfile.ZipFile, 'r'
    elif path.endswith('.tar.gz') or path.endswith('.tgz'):
        opener, mode = tarfile.open, 'r:gz'
    elif path.endswith('.tar.bz2') or path.endswith('.tbz'):
        opener, mode = tarfile.open, 'r:bz2'
    else: 
        raise ValueError, "Could not extract `%s` as no appropriate extractor is found" % path
    
    cwd = os.getcwd()
    
    try:
        file = opener(path, mode)
        try:
            os.chdir(targetdir)
            file.extractall()
        finally:
            file.close()
    finally:
        os.chdir(cwd)

if __name__ == "__main__":
    main()

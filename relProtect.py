#!/usr/bin/python

from yum.constants import TS_INSTALL,TS_TRUEINSTALL,TS_UPDATE,TS_OBSOLETING,TS_REMOVE_STATES
from yum.plugins import PluginYumExit,TYPE_INTERACTIVE,TYPE_CORE

requires_api_version = '2.6'
plugin_type = (TYPE_CORE,TYPE_INTERACTIVE)
expk = dict()
relstr = None

def config_hook(conduit):
	global relstr
	# Add command-line option for not doing PluginYumExit
	parser = conduit.getOptParser()
	parser.add_option('','--disable-release-protection',dest='yumexit',action='store_false',default=True,
		help='Disable Release Protection')
	parser.add_option('','--release',dest='relKey',action='store',default=None
		help='Specify release string. Overrides plugin config file')
	relstr = conduit.confString('main','release',default=None)

def preresolve_hook(conduit):
	global relstr
	ts = conduit.getTsInfo()
	opts,commands = conduit.getCmdLine()
	if opts.relKey != None:
		relstr = opts.relKey
	installs = ts.getMembersWithState(output_states=[TS_INSTALL,TS_TRUEINSTALL])
	updates = ts.getMembersWithState(output_states=[TS_UPDATE,TS_OBSOLETING])
	removes = ts.getMembersWithState(output_states=TS_REMOVE_STATES)
	if (len(installs)>0) and (relstr is not None):
		global expk
		for p in conduit.getPackages():
			if p.release.find(relstr)>0:
				expk[p.name] = p
		for pi in installs:
			if pi.name in expk:
				conduit.info(2,'Installation of package %s will deviate '\
					'from build' % pi.po)
				if opts.yumexit!=False:
					conduit.info(2,'Removing %s from install list' % pi.po)
					ts.remove(pi.pkgtup)
					conduit.info(2,'Adding %s to install list' % expk[pi.name])
					ts.addInstall(expk[pi.name])
	if (len(updates)!=0) and (len(removes)!=0):
		for pu in updates:
			for pr in removes:
				if pr.name == pu.name:
					protect = protect_release(pu,pr)
					if protect==True:
						conduit.info(2,'Upgrade of package %s will deviate '\
							'from build' % pu.name)
						if opts.yumexit != False:
							raise PluginYumExit('Upgrade operation terminated as new '\
								'package(s) will deviate from build')

def protect_release(new,old):
	global relstr
	if old.release.find(relstr) > 0:
		if new.release.find(relstr)<0:
			return True
	return False

def _check_ups_rem_rel(ups,rems):
	global relstr
	if relstr is not None:

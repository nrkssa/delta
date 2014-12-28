#!/usr/bin/env python

import os
import time
import subprocess
import numpy as np
from optparse import OptionParser
from pybedtools import *
#from lib.features import *
from lib.process import *

def set_optparser():
	'''Options setter
	'''
	usage = '''usage: %prog [options]
	'''
	optparser = OptionParser(version='%prog 1.0.1',usage=usage,add_help_option=False)
	optparser.add_option("-h","--help",action="help",
		help="show this help message and exit")
	optparser.add_option('-c','--chip_bed',dest='chip_beds',type='string',
		help='ChIP-seq bed file of histone modifications', default='NA')
	optparser.add_option('-R','--read', action="store_true", dest='read',
		help='Read existing training and predicting data instead of generate from ChIP-seq (default: False)',default=False)
	optparser.add_option('-E','--enhancer',dest='enhancer',type='string',
		help='BED file containing the enhancer loci',default='NA')
	optparser.add_option('-P','--promoter',dest='promoter',type='string',
		help='BED file containing the promoter loci',default='NA')
	optparser.add_option('-B','--background_size',dest='back_size',type='int',
		help='Number of random genomic regions distal to known TSS (default: 10000)',default=80000)
	optparser.add_option('-g','--genome',dest='genome',type='string',
		help='Genome assembly should be one of the followings: dm3, mm9, hg17, hg18, hg19',default='hg19')
	optparser.add_option('-b','--bin_size',dest='bin_size',type='int',
		help='Length of dividing bins (default: 100)',default=100)
	optparser.add_option('-w','--window_size',dest='win_size',type='int',
		help='Length of sliding window, should be integer times of bin size (default: 2000)',default=2000)
	optparser.add_option('--iteration_number',dest='iter_num',type='int',
		help='Number of iteration for AdaBoost (default: 100)',default=100)
	optparser.add_option('--pvalue_threshold',dest='p_thres',type='float',
		help='P-value threshold for enhancer prediction (default: 0.5)',default=0.5)
	optparser.add_option('-o','--output',dest='output',type='string',
		help='Output file name (default output file is "predicted_enhancer.bed")',default='predicted_enhancer.bed')
	return optparser

def main():
	# Parsing options
	options,args = set_optparser().parse_args()
	tmp_dir = 'tmp_dir'
	
	# Path setting
	real_dir = os.path.dirname(os.path.realpath(__file__))
	
	# Generating training and predicting data
	if options.read == False:
		chipNames = options.chip_beds.split(',')
		# Check options
		if options.win_size%options.bin_size != 0:
			sys.exit('Window size should be integer times of bin size')
		win = options.win_size/options.bin_size

		# Creat temporary directory
		if not os.path.exists(tmp_dir):
			os.makedirs(tmp_dir)
			print '@ ' + time.ctime(),
			print 'Folder "./' + tmp_dir + '" created.'
		
		# Calculating total count of reads
		print '@ ' + time.ctime(),
		print 'Calculating total count of reads in each BED file.'
		dictChip2Len = {}
		
		#CD4
		#dictChip2Len = {'H2AK5ac.chr1.bed':3426772,'H2AK9ac.chr1.bed':2060786,'H2BK120ac.chr1.bed':3426678,'H2BK12ac.chr1.bed':3600043,'H2BK20ac.chr1.bed':4061778,'H2BK5ac.chr1.bed':3315215,'H2BK5me1.chr1.bed':8868681,'H3K14ac.chr1.bed':3781522,'H3K18ac.chr1.bed':4228555,'H3K23ac.chr1.bed':2518309,'H3K27ac.chr1.bed':3432394,'H3K27me1.chr1.bed':9997998,'H3K27me2.chr1.bed':9027153,'H3K27me3.chr1.bed':8969379,'H3K36ac.chr1.bed':4355864,'H3K36me1.chr1.bed':8033868,'H3K36me3.chr1.bed':13570946,'H3K4ac.chr1.bed':3528870,'H3K4me1.chr1.bed':11320203,'H3K4me2.chr1.bed':5446927,'H3K4me3.chr1.bed':16841728,'H3K79me1.chr1.bed':5110747,'H3K79me2.chr1.bed':4694161,'H3K79me3.chr1.bed':5905785,'H3K9ac.chr1.bed':3950078,'H3K9me1.chr1.bed':9267232,'H3K9me2.chr1.bed':9739255,'H3K9me3.chr1.bed':6309689,'H3R2me1.chr1.bed':9507369,'H3R2me2.chr1.bed':6476651,'H4K12ac.chr1.bed':3662483,'H4K16ac.chr1.bed':7019538,'H4K20me1.chr1.bed':10911168,'H4K20me3.chr1.bed':5561246,'H4K5ac.chr1.bed':4100374,'H4K8ac.chr1.bed':4260895,'H4K91ac.chr1.bed':3169773,'H4R3me2.chr1.bed':7297121}
		
		#H1
		#dictChip2Len = {'H3K4me1.chr1.bed':16910668,'H3K4me2.chr1.bed':25788129,'H3K4me3.chr1.bed':23910645,'H2BK15ac.chr1.bed':26559811,'H3K23me2.chr1.bed':24199260,'H3K27ac.chr1.bed':15590912,'H3K27me3.chr1.bed':11356062,'H3K36me3.chr1.bed':14183808,'H3K4ac.chr1.bed':19562559,'H3K56ac.chr1.bed':20601724,'H3K79me1.chr1.bed':17285256,'H3K79me2.chr1.bed':17327532,'H3K9ac.chr1.bed':13878853,'H3K9me3.chr1.bed':24778009,'H4K20me1.chr1.bed':22569699,'H4K5ac.chr1.bed':25705736,'H4K8ac.chr1.bed':9548724,'H4K91ac.chr1.bed':23370795}

		for chipName in chipNames:
			chipBed = BedTool(chipName)
			dictChip2Len[chipName] = len(open(chipName).readlines())

		# Train data
		if options.enhancer != 'NA':
			trainData = []
			enhancerBed = loci2bed(options.enhancer, 'enhancer', options.bin_size, options.win_size, tmp_dir)
			promoterBed = loci2bed(options.promoter, 'promoter', options.bin_size, options.win_size, tmp_dir)
			sampleSize = options.back_size
			shuffledBedName = shuffle_window(options.promoter, options.enhancer, sampleSize, options.win_size, options.genome, real_dir, tmp_dir)
			shuffledBed = loci2bed(shuffledBedName, 'shuffled', options.bin_size, options.win_size, tmp_dir)

			for chipName in chipNames:
				print '@ ' + time.ctime(),
				print 'Calculating coverage of ' + chipName + ' at training targets and background region.'
				# Loading ChIP-seq BED file
				chipBed = BedTool(chipName)
				# Line count of ChIP-seq for normalization
				lineCount = dictChip2Len[chipName]
				# Enhancer
				# Count calculation
				BedTool(enhancerBed).window(chipBed,w=0,c=True,output=os.path.join(tmp_dir,'enhancer_count.bed'))
				enhancerProfileMat = profile_target(os.path.join(tmp_dir,'enhancer_count.bed'), os.path.join(tmp_dir,'enhancer_temp_bin.bed'), lineCount, options.bin_size, options.win_size)
				# Calculate parameters
				enhancerFeatureKurt, enhancerFeatureSkew, enhancerFeatureBimo, enhancerFeatureItst = shape_mat(enhancerProfileMat, win)

				# Promoter
				# Count calculation
				BedTool(promoterBed).window(chipBed,w=0,c=True,output=os.path.join(tmp_dir,'promoter_count.bed'))
				promoterProfileMat = profile_target(os.path.join(tmp_dir,'promoter_count.bed'), os.path.join(tmp_dir,'promoter_temp_bin.bed'), lineCount, options.bin_size, options.win_size)
				# Calculate parameters
				promoterFeatureKurt, promoterFeatureSkew, promoterFeatureBimo, promoterFeatureItst = shape_mat(promoterProfileMat, win)

				# Background window
				# Coverage calculation
				BedTool(shuffledBed).window(chipBed,w=0,c=True,output=os.path.join(tmp_dir,'shuffled_count.bed'))
				shuffledProfileMat = profile_target(os.path.join(tmp_dir,'shuffled_count.bed'), os.path.join(tmp_dir,'shuffled_temp_bin.bed'), lineCount, options.bin_size, options.win_size)
				# Calculate parameters
				shuffledFeatureKurt, shuffledFeatureSkew, shuffledFeatureBimo, shuffledFeatureItst = shape_mat(shuffledProfileMat, win)

				if len(trainData) == 0:
					for i in range(0, len(enhancerProfileMat)):
						trainData.append(['1',enhancerFeatureItst[i],enhancerFeatureKurt[i],enhancerFeatureSkew[i],enhancerFeatureBimo[i]])
					for i in range(0, len(promoterProfileMat)):
						trainData.append(['0',promoterFeatureItst[i],promoterFeatureKurt[i],promoterFeatureSkew[i],promoterFeatureBimo[i]])
					for i in range(0, len(shuffledProfileMat)):
						trainData.append(['0',shuffledFeatureItst[i],shuffledFeatureKurt[i],shuffledFeatureSkew[i],shuffledFeatureBimo[i]])
				else:
					for i in range(0, len(enhancerProfileMat)):
						trainData[i].append(enhancerFeatureItst[i])
						trainData[i].append(enhancerFeatureKurt[i])
						trainData[i].append(enhancerFeatureSkew[i])
						trainData[i].append(enhancerFeatureBimo[i])
					for i in range(0, len(promoterProfileMat)):
						trainData[len(enhancerProfileMat)+i].append(promoterFeatureItst[i])
						trainData[len(enhancerProfileMat)+i].append(promoterFeatureKurt[i])
						trainData[len(enhancerProfileMat)+i].append(promoterFeatureSkew[i])
						trainData[len(enhancerProfileMat)+i].append(promoterFeatureBimo[i])
					for i in range(0, len(shuffledProfileMat)):
						trainData[len(enhancerProfileMat)+len(promoterProfileMat)+i].append(shuffledFeatureItst[i])
						trainData[len(enhancerProfileMat)+len(promoterProfileMat)+i].append(shuffledFeatureKurt[i])
						trainData[len(enhancerProfileMat)+len(promoterProfileMat)+i].append(shuffledFeatureSkew[i])
						trainData[len(enhancerProfileMat)+len(promoterProfileMat)+i].append(shuffledFeatureBimo[i])
			write_plain_format(trainData, 'trainData'+str(options.win_size)+'.txt')

		# Predict data

			# Binning genome
			print '@ ' + time.ctime(),
			print "Bining genome."
			binName = bin_genome(options.genome, options.bin_size, options.win_size, tmp_dir)
			predictData = []
			targetPosMat = []
			for chipName in chipNames:
				# Line count of ChIP-seq for normalization
				lineCount = dictChip2Len[chipName]
				# Loading ChIP-seq BED file
				chipBed = BedTool(chipName)
				# Coverage calculation
				print '@ ' + time.ctime(),
				print 'Calculating counts of ' + chipName
				hm = chipName.split('/')[-1].split('.')[0]
				if hm.find('h3k4me1') != -1:
					hm = 'H3K4me1'
				elif hm.find('h3k4me2') != -1:
					hm = 'H3K4me2'
				elif hm.find('h3k4me3') != -1:
					hm = 'H3K4me3'
				countFile = os.path.join(tmp_dir, options.genome+'_'+hm+'_count.bed')
				if not os.path.exists(countFile):
					BedTool(binName).window(chipBed,w=0,c=True,output=countFile)
				print '@ ' + time.ctime(),
				print 'Profiling sliding windows'
				featureFile = os.path.join(tmp_dir, options.genome+'_'+hm+'_feature.txt')
				profile_sliding_window(countFile, lineCount, win, options.bin_size, featureFile)

	if options.enhancer != 'NA':
		# Creat R script for AdaBoost
		rscript = open('adaboost.R','w')
		print >> rscript, 'library(ada)'
		print >> rscript, 'tdata <- read.table("trainData.txt")'
		print >> rscript, 'pdata <- read.table("predictData.txt")'
		print >> rscript, 'nc <- dim(tdata)[2]'
		print >> rscript, 'colnames(pdata) <- colnames(tdata[,2:nc])'
		print >> rscript, 'adamodel <- ada(x=tdata[,2:nc],y=tdata[,1],iter=%s)' % options.iter_num
		print >> rscript, 'adapred <- predict(adamodel, newdata=pdata,type="probs")'
		print >> rscript, 'write.table(adapred[,2],"pred",quote=F,row.names=F,col.names=F)'
		rscript.close()

		print '@ ' + time.ctime(),
		print 'Model training and predicting.'
		
		# Execution of AdaBoost
		p = subprocess.Popen('Rscript adaboost.R', shell=True)
		p.wait()
		
		# Prediction interpretation and output
		adapred = open('pred','r')
		fout = open(options.output,'w')
		outfileTarget = open(os.path.join(tmp_dir, options.genome+'_target.bed'),'r')
		for prob in adapred:
		 	ln = outfileTarget.next().strip()
		 	prob = float(prob.strip())
		 	if prob >= options.p_thres:
		 		print >> fout, ln
		fout.close()
		outfileTarget.close()
		adapred.close()

if __name__ == '__main__':
	main()

import epub
import os
import sys
from genshi.template import TemplateLoader

class Section:

    def __init__(self):
        self.title = ''
        self.subsections = []
        self.css = ''
        self.text = []
        self.html = False
        self.templateFileName = 'ez-section.html'
        
class Book:
    
    def __init__(self):
        self.impl = epub.EpubBook()
        self.title = ''
        self.authors = []
        self.cover = ''
        self.lang = 'en-US'
        self.sections = []
        self.templateLoader = TemplateLoader(os.path.join(sys.path[0], 'templates'))
      
    def __addSection(self, section, id, depth):
        if depth > 0:
            if not section.html:
              stream = self.templateLoader.load(section.templateFileName).generate(section = section)
              html = stream.render('xhtml', doctype = 'xhtml11', drop_xml_decl = False)
            else:
              html = section.text
            item = self.impl.addHtml('', '%s.html' % id, html)
            self.impl.addSpineItem(item)
            self.impl.addTocMapNode(item.destPath, section.title, depth)
            id += '.'
        if len(section.subsections) > 0:
            for i, subsection in enumerate(section.subsections):
                self.__addSection(subsection, id + str(i + 1), depth + 1)
    
    def make(self, outputDir, do_epub):
        outputFile = outputDir + '.epub'
        
        self.impl.setTitle(self.title)
        self.impl.setLang(self.lang)
        for author in self.authors:
            self.impl.addCreator(author)
        if self.cover:
            self.impl.addCover(self.cover)
        self.impl.addTitlePage()
        self.impl.addTocPage()
        root = Section()
        root.subsections = self.sections
        self.__addSection(root, 's', 0)
        self.impl.createBook(outputDir)
        if do_epub:
          self.impl.createArchive(outputDir, outputFile)

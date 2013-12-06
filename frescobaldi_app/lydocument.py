# This file is part of the Frescobaldi project, http://www.frescobaldi.org/
#
# Copyright (c) 2013 - 2013 by Wilbert Berendsen
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# See http://www.gnu.org/licenses/ for more information.

"""
LyDocument

Provides a ly.document.Document api for a QTextDocument (or: more specifically
a Frescobaldi document.Document).

This can be used to perform operations from the ly module on a loaded
Frescobaldi document.

You don't need to save a LyDocument instance. Just create it and use it,
then discard it.

"""

from __future__ import unicode_literals
from __future__ import absolute_import

from PyQt4.QtGui import QTextCursor

import ly.document
import tokeniter
import highlighter


def cursor(cursor, select_all=True):
    """Return a ly.document.Cursor for the specified QTextCursor.
    
    The ly Cursor is instantiated with a LyDocument proxying for the
    original cursors document.
    
    So you can call all operations in the ly module and they will work on a
    Frescobaldi document (which is a subclass of QTextDocument).
    
    If select_all is True (the default), the ly Cursor selects the whole 
    document if the original cursor has no selection.
    
    """
    doc = LyDocument(cursor.document())
    if not select_all or cursor.hasSelection():
        start, end = cursor.selectionStart(), cursor.selectionEnd()
    else:
        start, end = 0, None
    return ly.document.Cursor(doc, start, end)
    

class LyDocument(ly.document.DocumentBase):
    """LyDocument proxies a loaded Frescobaldi document (QTextDocument).
    
    This is used to let the tools in the ly module operate on Frescobaldi
    documents.
    
    Creating a LyDocument is very fast, you do not need to save it. When 
    applying the changes, LyDocument starts an editblock, so that the 
    operations appears as one undo-item.
    
    It is recommended to not nest calls to QTextCursor.beginEditBlock(), as 
    the highlighter is not called to update the tokens until the last 
    endEditBlock() is called.
    
    Therefore LyDocument provides a simple mechanism for combining several 
    change operations via the combine_undo attribute.
    
    If combine_undo is None (the default), the first time changes are applied
    QTextCursor.beginEditBlock() will be called, but subsequent times 
    QTextCursor.joinPreviousEditBlock() will be used. So the highlighter 
    updates the tokens between the operations, but they will appear as one 
    undo-item.
    
    If you want to combine the very first operation already with an earlier 
    change, set combine_undo to True before the changes are applied (e.g. 
    before entering or exiting the context).
    
    If you do not want to combine operations into a single undo-item at all,
    set combine_undo to False.
    
    (Of course you can nest calls to QTextCursor.beginEditBlock(), but in 
    that case the tokens will not be updated between your operations. If 
    your operations do not depend on the tokens, it is no problem 
    whatsoever. The tokens *are* updated after the last call to 
    QTextCursor.endEditBlock().)
    
    """
    
    def __init__(self, document):
        self._d = document
        super(LyDocument, self).__init__()
        self.combine_undo = None
    
    def __len__(self):
        """Return the number of blocks"""
        return self._d.blockCount()
    
    def __getitem__(self, index):
        """Return the block at the specified index."""
        return self._d.findBlockByNumber(index)
        
    def plaintext(self):
        """The document contents as a plain text string."""
        return self._d.toPlainText()

    def setplaintext(self, text):
        """Sets the document contents to the text string."""
        self._d.setPlainText(text)

    def size(self):
        """Return the number of characters in the document."""
        return self._d.characterCount()

    def block(self, position):
        """Return the text block at the specified character position.
        
        The text block itself has no methods, but it can be used as an
        argument to other methods of this class.
        
        (Blocks do have to support the '==' operator.)
        
        """
        return self._d.findBlock(position)
    
    def index(self, block):
        """Return the linenumber of the block (starting with 0)."""
        return block.blockNumber()
         
    def position(self, block):
        """Return the position of the specified block."""
        return block.position()

    def text(self, block):
        """Return the text of the specified block."""
        return block.text()
    
    def next_block(self, block):
        """Return the next block, which may be invalid."""
        return block.next()
    
    def previous_block(self, block):
        """Return the previous block, which may be invalid."""
        return block.previous()
    
    def isvalid(self, block):
        """Return True if the block is a valid block."""
        return block.isValid()
    
    def apply_changes(self):
        """Apply the changes and update the tokens."""
        c = QTextCursor(self._d)
        c.joinPreviousEditBlock() if self.combine_undo else c.beginEditBlock()
        try:
            changes = sorted(self._changes.items(), reverse=True)
            for start, items in changes:
                for end, text in items:
                    c.movePosition(QTextCursor.End) if end is None else c.setPosition(end)
                    c.setPosition(start, QTextCursor.KeepAnchor)
                    c.insertText(text)
        finally:
            c.endEditBlock()
            if self.combine_undo is None:
                self.combine_undo = True
        
    def tokens(self, block):
        """Return the tuple of tokens of the specified block."""
        return tokeniter.tokens(block)
        
    def initial_state(self):
        """Return the state at the beginning of the document."""
        return highlighter.highlighter(self._d).initialState()
        
    def state(self, block):
        """Return the state at the start of the specified block."""
        return tokeniter.state(block)
            
    def state_end(self, block):
        """Return the state at the end of the specified block."""
        return tokeniter.state_end(block)

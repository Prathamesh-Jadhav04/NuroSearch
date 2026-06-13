"""
NuroSearch Query Language Parser
Supports SQL-like syntax for vector search operations.
Uses SLY (Python Lex-Yacc) for lexing and parsing.
"""

import re
from sly import Lexer, Parser

class NuroLexer(Lexer):
    """Tokenizer for NuroSearch Query Language."""
    
    reflags = re.IGNORECASE
    
    tokens = {
        SELECT, FROM, WHERE, AND, LIMIT,
        EQ, NEQ, GT, LT, GTE, LTE,
        IDENT, NUMBER, STRING, STAR
    }
    ignore = ' \t'
    ignore_comment = r'\#.*'
    
    # Keywords
    SELECT  = r'SELECT'
    FROM    = r'FROM'
    WHERE   = r'WHERE'
    AND     = r'AND'
    LIMIT   = r'LIMIT'
    
    # Operators
    GTE = r'>='
    LTE = r'<='
    NEQ = r'!='
    GT  = r'>'
    LT  = r'<'
    EQ  = r'='
    
    STAR   = r'\*'
    IDENT  = r'[a-zA-Z_][a-zA-Z0-9_]*'
    
    @_(r'\d+(\.\d+)?')
    def NUMBER(self, t):
        t.value = float(t.value)
        return t
        
    @_(r"'[^']*'")
    def STRING(self, t):
        t.value = t.value.strip("'")
        return t
        
    ignore_newline = r'\n+'

class NuroParser(Parser):
    tokens = NuroLexer.tokens
    
    # Enable debugging mode
    debugfile = None
    
    @_('SELECT fields FROM IDENT where_clause limit_clause')
    def statement(self, p):
        return {
            'type': 'SELECT',
            'fields': p.fields,
            'table': p.IDENT,
            'where': p.where_clause,
            'limit': p.limit_clause
        }
        
    @_('STAR')
    def fields(self, p):
        return '*'
        
    @_('IDENT')
    def fields(self, p):
        return [p.IDENT]
        
    @_('WHERE conditions')
    def where_clause(self, p):
        return p.conditions
        
    @_('')
    def where_clause(self, p):
        return []
        
    @_('condition')
    def conditions(self, p):
        return [p.condition]
        
    @_('conditions AND condition')
    def conditions(self, p):
        return p.conditions + [p.condition]
        
    @_('IDENT EQ STRING')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '=', 'value': p.STRING}
        
    @_('IDENT EQ NUMBER')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '=', 'value': p.NUMBER}
        
    @_('IDENT GT NUMBER')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '>', 'value': p.NUMBER}
        
    @_('IDENT LT NUMBER')
    def condition(self, p):
        return {'field': p.IDENT, 'op': '<', 'value': p.NUMBER}
        
    @_('LIMIT NUMBER')
    def limit_clause(self, p):
        return int(p.NUMBER)
        
    @_('')
    def limit_clause(self, p):
        return 10

def compile_to_api_call(ast: dict) -> dict:
    """
    Compile AST node to NuroSearch API parameters.
    
    Example:
        SELECT * FROM documents WHERE category = 'sports' AND similarity > 0.82 LIMIT 5
        →
        {
            "endpoint": "/search",
            "params": {"filter_category": "sports", "min_similarity": 0.82, "k": 5}
        }
    """
    if not ast:
        return {}
        
    if ast['type'] == 'SELECT':
        params = {
            'k': ast.get('limit', 10),
            'algo': 'hnsw',
            'metric': 'cosine'
        }
        
        for condition in ast.get('where') or []:
            field = condition['field'].lower()
            op = condition['op']
            val = condition['value']
            
            if field == 'category':
                params['filter_category'] = val
            elif field in ('similarity', 'score'):
                params['min_similarity'] = val
            elif field == 'algo':
                params['algo'] = val
            elif field == 'metric':
                params['metric'] = val
                
        return {
            "endpoint": "/search",
            "params": params
        }
        
    return {}

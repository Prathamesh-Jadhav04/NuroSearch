import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from query_parser import NuroLexer, NuroParser, compile_to_api_call

def test_lexer():
    lexer = NuroLexer()
    tokens = list(lexer.tokenize("SELECT * FROM documents WHERE category = 'sports' LIMIT 5"))
    assert len(tokens) == 10
    assert tokens[0].type == 'SELECT'
    assert tokens[1].type == 'STAR'
    assert tokens[2].type == 'FROM'
    assert tokens[3].type == 'IDENT'
    assert tokens[4].type == 'WHERE'
    assert tokens[5].type == 'IDENT'
    assert tokens[6].type == 'EQ'
    assert tokens[7].type == 'STRING'
    assert tokens[8].type == 'LIMIT'
    assert tokens[9].type == 'NUMBER'

def test_parser_and_compile():
    lexer = NuroLexer()
    parser = NuroParser()
    
    query = "SELECT * FROM vectors WHERE category = 'sports' AND similarity > 0.85 LIMIT 3"
    tokens = lexer.tokenize(query)
    ast = parser.parse(tokens)
    
    assert ast['type'] == 'SELECT'
    assert ast['table'] == 'vectors'
    assert ast['limit'] == 3
    assert len(ast['where']) == 2
    assert ast['where'][0]['field'] == 'category'
    assert ast['where'][0]['value'] == 'sports'
    assert ast['where'][1]['field'] == 'similarity'
    assert ast['where'][1]['value'] == 0.85
    
    api_call = compile_to_api_call(ast)
    assert api_call['endpoint'] == '/search'
    assert api_call['params']['filter_category'] == 'sports'
    assert api_call['params']['min_similarity'] == 0.85
    assert api_call['params']['k'] == 3

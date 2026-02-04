"""
# wS
## Parser

Allows to parse wS.

### Functions

```
loads(wS : str) # loads wS from a str

load(file : pathlib.Path | str, encoding : str [optionnal]) # loads wS from a file
```

### Others

- `Warning` : 
  - `LoadFileWarning`
- `Exception` : 
  - `LoadFileError`
"""

WHITESPACE = ['\t', '\n', '\r', '\v', '\f', ' ', '/u00A0']
"""wS whitespace"""
SEPARATOR  = [',', ';', '|']
"""wS separators"""
DEFINER    = [':']
"""wS definers""" 

from ...exceptions import LoadFileWarning, LoadFileError

def loads(wS : str, permissiveSyntax : bool = False):
    """
    # Loads
    Loads in-string wS. 

    ## Arguments
    - `wS` : str
        - wS string to parse, regardless of version.
    - `permissiveSyntax` : bool
        - allows permissive Syntax (avoid some errors).

    Automatically converts accurate `int` | `float`.
    wS supports both lists and dicts.

    May raise `LoadFileWarning`, `LoadFileError`.
    """
    from warnings import warn
    # Vars
    i : int = 0
    n : int = len(wS)

    class Inherit : pass

    class Alias   : pass

    class Path () :
        """Path class for resolving references within wS data structures."""

        def __init__(self, initial : list[int | str] = None):
            self.signs : list[int | str] = initial if initial is not None else [].copy()

        def append(self, sign : int | str) :
            """Appends a sign to the path."""
            self.signs.append(sign)

        def pop(self) :
            """Pops the last sign from the path and returns it."""
            return self.signs.pop()
        
        def top(self) :
            """Returns the last sign from the path."""
            if len(self.signs) > 0 : return self.signs[-1]
            else                   : return 'void'
        
        def isEmpty(self) : 
            """Returns if the path is empty."""
            return len(self.signs) == 0
        
        def get(self, obj : dict | list) : 
            """Resolves the path on the given object and returns the referenced value."""
            last = ':root'
            for sign in self.signs :
                if isinstance(sign, int) :
                    if isinstance(obj, list) :
                        if sign < len(obj) :
                            obj = obj[sign]
                        else : 
                            raise LoadFileError(f"Unable to resolve path '{self}', index '{sign}' out of range in {last}.")
                    elif isinstance(obj, dict) :
                        if sign in obj : 
                            obj = obj[sign]
                        elif str(sign) in obj :
                            obj = obj[str(sign)]
                        else : 
                            raise LoadFileError(f"Unable to resolve path '{self}', key '{sign}' not found in {last}.")
                    else : 
                        raise LoadFileError(f"Unable to resolve path '{self}', unexpected type in {last}.")
                elif isinstance(sign, str) :
                    if isinstance(obj, dict) :
                        if sign in obj : 
                            obj = obj[sign]
                        else : 
                            raise LoadFileError(f"Unable to resolve path '{self}', key '{sign}' not found in {last}.")
                    else : 
                        raise LoadFileError(f"Unable to resolve path '{self}', unexpected type in {last}.")
                last = str(sign)
            return obj
        
        def copy(self):
            return Path(self.signs.copy())

        def __repr__(self):
            return '.'.join([str(s) for s in self.signs])
        
        def __iter__(self) :
            return iter(self.signs)
        
    def get_name(value : str):
        """Resolves a name from its string representation."""
        try    : return int(value)
        except : return value
        
    def get_value(obj : dict | list, path, value : str, key):
        """Resolves a value from its string representation."""
        if len(value) > 0 :
            if value[0] == '?' :
                if   value in ['?true', '?1']  : return True
                elif value in ['?false', '?0'] : return False
                elif value == '?empty'     : return ''
                elif value == '?void'      : return ''
                elif value == '?null'      : return None
                elif value == '?nil'       : return None
                elif value == '?nilhus'    : return None
                elif value == '?undefined' : return None
                elif value == '?iskey'     : return {}
                elif value == '?isroot'    : return {}
                elif value == '?dict'      : return {}
                elif value == '?iter'      : return []
                elif value == '?inherit'   : 
                    val = Inherit
                    loc = obj
                    top = path.top()
                    for sign in path :
                        if   isinstance(loc, list) :
                            try    :
                                i_key = int(key)
                                if 0<= i_key and i_key < len(loc) :
                                    val = loc[i_key]
                            except :
                                pass
                            loc = loc[sign]
                        elif isinstance(loc, dict) :
                            if key in loc :
                                val = loc[key]
                            elif top in loc :
                                sub = loc[top]
                                if   isinstance(sub, list) : 
                                    try    :
                                        i_key = int(key)
                                        if 0<= i_key and i_key < len(sub) :
                                            val = sub[i_key]
                                    except :
                                        pass
                                elif isinstance(sub, dict) :
                                    if key in sub :
                                        val = sub[key]
                            loc = loc[sign]
                    if val is Inherit :
                        raise LoadFileError(f'wS error : at {path}.{key}, unable to resolve inherit.')
                    return val
                else :
                    raise LoadFileError(f'wS error : at {path}, unknown special value "{value}".')
            else : 
                try    : return int(value)
                except : 
                    try    : return float(value)
                    except : return value
        else :
            return ''

    def read_alias(wS : str, i : int, current_path : Path, key : str | int):
        """Parses an alias."""
        if wS[i] != '(' : raise LoadFileError(f'wS error : at {i}, ghost alias')
        j = i + 1
        buffer     = ''
        alias_path = Path()
        key_path   = current_path.copy()
        key_path.append(key)
        while j < n : 
            chr = wS[j]
            if chr == '.' :
                if alias_path.isEmpty() and len(buffer) == 0 :
                    alias_path = current_path.copy()
                else : 
                    alias_path.append(get_name(buffer))
                    buffer = ''
            elif chr == ')' :
                if len(buffer) > 0 :
                    alias_path.append(get_name(buffer))
                if alias_path.isEmpty() : raise LoadFileError(f'wS error : at {i}, empty alias')
                return j, (key_path, alias_path)
            else :
                buffer += chr
            j += 1
        raise LoadFileError(f'wS error : at {i}, unclosed alias')
        
    is_pending : bool = False
    pending_bf : str  = ''
    is_comment : bool = False
    comment_bf : str  = ''
    is_string  : bool = False
    string_bf  : str  = ''
    is_value   : bool = False
    value_bf   : str  = ''
    is_name    : bool = False
    name_bf    : str  = ''

    item_count : int  = 0
    already_closed    = False

    path : Path                = Path([])
    type : Path                = Path([])
    obj  : dict | list | None  = None
    aliases : list[Path, Path] = []
    was_inited : bool          = False
    
    while i < n :
        chr = wS[i]
        # process chr
        if   is_comment :
            if chr == comment_bf : 
                is_comment = False
                comment_bf = ''
        elif chr == '\\' :
            already_closed = False
            i        += 1
            is_value  = True
            if is_pending :
                value_bf += pending_bf
                is_pending, pending_bf = (False, '')
            value_bf += wS[i]
        elif is_string :
            if chr == string_bf :
                is_string = False
                string_bf = ''
            else :
                value_bf += chr
        elif chr in ['"', "'"] :
            is_string  = True
            is_value   = True
            is_pending = False
            pending_bf = ''
            string_bf = chr
            already_closed = False
        elif chr == '/' :
            is_comment = True
            comment_bf = chr
        elif chr in SEPARATOR :
            if not was_inited : raise LoadFileError(f'wS error : at {i}, sep in void.')
            if not already_closed :
                if   type.top() == 'iter' : 
                    if is_name  : raise LoadFileError(f'wS error : at {i}, name in iterable.')
                    if is_value :
                        sub = path.get(obj)
                        sub.append(get_value(obj, path, value_bf, len(sub)))
                elif type.top() == 'dict' :
                    if is_name and is_value :
                        sub = path.get(obj)
                        sub[name_bf] = get_value(obj, path, value_bf, name_bf)
                    elif is_value :
                        sub[get_name(value_bf)] = None
                    else : raise LoadFileError(f'wS error : at {i}, sep on nilhus ("{wS[i-20:i+20]}").')
            already_closed = False
            is_name = False
            name_bf = ''
            is_value = False
            value_bf = ''
            is_pending = False
            pending_bf = ''
        elif chr in DEFINER :
            if not was_inited : raise LoadFileError(f'wS error : at {i}, set in void.')
            already_closed = False
            if   type.top() == 'iter' : 
                raise LoadFileError(f'wS error : at {i}, set in iterable.')
            elif type.top() == 'dict' :
                if is_value : 
                    if is_name : raise LoadFileError(f'wS error : at {i}, double set')
                    is_name = True
                    name_bf = get_name(value_bf)
                else : raise LoadFileError(f'wS error : at {i}, set on nilhus')
            is_value = False
            value_bf = ''
            is_pending = False
            pending_bf = ''
        elif chr in ['[', '{'] :
            if permissiveSyntax : already_closed = True
            if   not was_inited :
                was_inited = True
                if   chr == '{' :
                    type.append('dict')
                    obj = {}
                elif chr == '[' :
                    type.append('iter')
                    obj = []
            elif type.top() == 'iter' : 
                try : sub = path.get(obj)
                except Exception as e :
                    raise LoadFileError(f'wS error : at {i}, in list, unable to access iterable subpath.') from e
                path.append(len(sub))
                if chr == '[' :
                    type.append('iter')
                    sub.append([])
                elif chr == '{' :
                    type.append('dict')
                    sub.append({})
            elif type.top() == 'dict' :
                try : sub = path.get(obj)
                except Exception as e :
                    raise LoadFileError(f'wS error : at {i}, in dict, unable to access iterable subpath.') from e
                key = name_bf if is_name else value_bf if is_value else None
                if key is None :
                    raise LoadFileError(f'wS error : at {i}, opening without key bind.')
                path.append(key)
                if chr == '[' :
                    type.append('iter')
                    sub[key] = []
                elif chr == '{' :
                    type.append('dict')
                    sub[key] = {}
            else :
                raise LoadFileError(f'wS error : at {i}, opening on void')
            is_name = False
            name_bf = ''
            is_value = False
            value_bf = ''
            is_pending = False
            pending_bf = ''
        elif chr in [']', '}'] :
            if not was_inited or type.isEmpty() : raise LoadFileError(f'wS error : at {i}, close "{chr}" in void.')
            if is_value :
                if   type.top() == 'iter' and chr == ']' : 
                    if is_name  : raise LoadFileError(f'wS error : at {i}, name in iterable.')
                    if is_value :
                        sub = path.get(obj)
                        sub.append(get_value(obj, path, value_bf, len(sub)))
                elif type.top() == 'dict' and chr == '}' :
                    sub = path.get(obj)
                    if is_name and is_value :    
                        sub[name_bf] = get_value(obj, path, value_bf, name_bf)
                    elif is_value :
                        sub[value_bf] = None
                else :
                    if chr == ']': raise LoadFileError(f'wS error : at {i}, mismatched closer (expected "{'}'}", got "{']'}").')
                    if chr == '}': raise LoadFileError(f'wS error : at {i}, mismatched closer (expected "{']'}", got "{'}'}").')
            already_closed = True
            is_name = False
            name_bf = ''
            is_value = False
            value_bf = ''
            is_pending = False
            pending_bf = ''
            type.pop()
            if type.isEmpty() :  
                if len(aliases) > 0 :
                    for alias in aliases :
                        path = alias[0]
                        key  = path.pop() 
                        src  = alias[1]
                        try :
                            src_obj = src.get(obj)
                        except Exception as e :
                            raise LoadFileError(f'wS error : alias at "{path}.{key}" to "{src}" is broken.') from e
                        if src_obj is Alias :
                            raise LoadFileError(f'wS error : alias at {path}.{key} src is "{src}", which is already an alias.')
                        sub = path.get(obj)
                        if   isinstance(sub, (list, dict)) : sub[key] = src_obj
                        else : raise LoadFileError(f'wS error : alias at "{path}.{key} is in the soup.')
                return obj
            else :
                path.pop()
        elif chr == '@' : # copy
            in_type = type.top()
            if not was_inited                       : raise LoadFileError(f'wS error : at {i}, copy in void.')
            if not is_name    and in_type == 'dict' :
                if is_value :
                    is_name  = True
                    name_bf  = get_name(value_bf)
                    value_bf = ''
                else :
                    raise LoadFileError(f'wS error : at {i}, copy in name.')
            i, paths  = read_alias(wS, i+1, path, name_bf if in_type == 'dict' else len(path.get(obj)))
            path_copy = paths[1]
            try : 
                obj_copy = path_copy.get(obj)
            except Exception as e : 
                raise LoadFileError(f'wS error : at {i}, copy path "{path_copy}" is broken.') from e
            if obj_copy is Alias or isinstance(obj_copy, (list, dict)) : raise LoadFileError(f'wS error : at {i}, copy path "{path_copy}" is an alias or a complex object.')
            is_value   = True
            value_bf  += str(obj_copy)
            is_pending = False
            pending_bf = ''
        elif chr == '(' : # alias
            in_type = type.top()
            if not was_inited                       : raise LoadFileError(f'wS error : at {i}, copy in void.')
            if not is_name    and in_type == 'dict' :
                if is_value : 
                    is_name = True
                    name_bf = get_name(value_bf)
                else :
                    raise LoadFileError(f'wS error : at {i}, copy in name.')
            i, paths = read_alias(wS, i, path, name_bf if in_type == 'dict' else len(path.get(obj)))
            aliases.append(paths)
            if   in_type == 'iter' : 
                    sub = path.get(obj)
                    sub.append(Alias)
            elif in_type == 'dict' :
                    sub = path.get(obj)
                    sub[name_bf] = Alias
            already_closed = True
            is_name = False
            name_bf = ''
            is_value = False
            value_bf = ''
            is_pending = False
            pending_bf = ''
        elif chr in WHITESPACE : 
            if is_value :
                is_pending = True
            if is_pending :
                pending_bf += ' '
        else : 
            already_closed = False
            is_value = True
            if is_pending :
                    value_bf += pending_bf
                    is_pending, pending_bf = (False, '')
            value_bf += ' '         
        #
        i += 1
    #
    raise LoadFileError('wS error : unclosed wS file')

from optparse import OptionParser, make_option
import sys, inspect, re, os

single_char_prefix_re = re.compile('^[a-zA-Z0-9]_')

class ErrorCollectingOptionParser(OptionParser):
    def __init__(self, *args, **kwargs):
        self._errors = []
        self._custom_names = {}
        # can't use super() because OptionParser is an old style class
        OptionParser.__init__(self, *args, **kwargs)
    
    def parse_args(self, argv):
        options, args = OptionParser.parse_args(self, argv)
        for k,v in options.__dict__.iteritems():
            if k in self._custom_names:
                options.__dict__[self._custom_names[k]] = v
                del options.__dict__[k]
        return options, args

    def error(self, msg):
        self._errors.append(msg)

def func_to_optionparser(func, prog=None):
    args, varargs, varkw, defaultvals = inspect.getargspec(func)
    defaultvals = defaultvals or ()
    options = dict(zip(args[-len(defaultvals):], defaultvals))
    argstart = 0
    if func.__name__ == '__init__':
        argstart = 1
    if defaultvals:
        required_args = args[argstart:-len(defaultvals)]
    else:
        required_args = args[argstart:]
    
    # Build the OptionParser:
    opt = ErrorCollectingOptionParser(usage=func.__doc__, prog=prog)
    
    helpdict = getattr(func, 'optfunc_arghelp', {})
    
    # Add the options, automatically detecting their -short and --long names
    shortnames = set(['h'])
    for funcname, example in options.items():
        # They either explicitly set the short with x_blah...
        name = funcname
        if single_char_prefix_re.match(name):
            short = name[0]
            name = name[2:]
            opt._custom_names[name] = funcname
        # Or we pick the first letter from the name not already in use:
        else:
            for short in name:
                if short not in shortnames:
                    break
        
        shortnames.add(short)
        short_name = '-%s' % short
        long_name = '--%s' % name.replace('_', '-')
        if example in (True, False, bool):
            action = 'store_true'
        else:
            action = 'store'
        opt.add_option(make_option(
            short_name, long_name, action=action, dest=name, default=example,
            help = helpdict.get(funcname, '')
        ))
   
    return opt, required_args, varargs is not None

def resolve_args(func, argv, interspersed_args=True, prog=None):
    parser, required_args, has_varargs = func_to_optionparser(func, prog=prog)
    if not interspersed_args:
        parser.disable_interspersed_args()
    options, args = parser.parse_args(argv)
    
    # Do we have correct number af required args?
    if len(required_args) != len(args) and not \
            (has_varargs and len(required_args) <= len(args)):
        if not hasattr(func, 'optfunc_notstrict'):
            parser._errors.append('Required %d arguments, got %d' % (
                len(required_args), len(args)
            ))

    # Ensure there are enough arguments even if some are missing
    args += [None] * (len(required_args) - len(args))
    return args, options.__dict__, parser._errors

def run(func, argv=None, stderr=sys.stderr, include_func_name_in_errors=False,
        prog=None):
    if argv is None:
        argv = sys.argv[1:]
    interspersed_args = True

    # Deal with multiple functions
    if isinstance(func, (tuple, list)):
        func = _master_func(func, prog=prog)
        interspersed_args = False

    if inspect.isfunction(func):
        args, kw, errors = resolve_args(func, argv, 
                                        interspersed_args=interspersed_args,
                                        prog=prog)
    elif inspect.isclass(func):
        if hasattr(func, '__init__'):
            args, kw, errors = resolve_args(func.__init__, argv,
                                            interspersed_args=interspersed_args,
                                            prog=prog)
        else:
            args, kw, errors = [], {}, []
    else:
        raise TypeError('arg is not a Python function or class')
    
    if not errors:
        try:
            return func(*args, **kw)
        except Exception, e:
            if include_func_name_in_errors:
                stderr.write('%s: ' % func.__name__)
            stderr.write(str(e) + '\n')
    else:
        if include_func_name_in_errors:
            stderr.write('%s: ' % func.__name__)
        stderr.write("%s\n" % '\n'.join(errors))

# Subcommand support
def _master_func(subcommands, prog=None):
    funcs = dict([
        (fn.__name__, fn) for fn in subcommands
    ])

    if prog is None:
        prog = os.path.basename(sys.argv[0])

    def master(cmd, *argv):
        if cmd not in funcs:
            names = ["'%s'" % fn.__name__ for fn in func]
            s = ', '.join(names[:-1])
            if len(names) > 1:
                s += ' or %s' % names[-1]
            stderr.write("Unknown command: try %s\n" % s)
            return
        run(funcs[cmd], argv=list(argv), include_func_name_in_errors=True,
            prog="%s %s" % (prog, cmd))

    doc = ["Commands:"]
    max_name_len = max([len(fn.__name__) for fn in subcommands])
    max_desc_len = min(5, 80-max_name_len)
    fmt_str = "  %%%ds  %%s" % max_name_len

    for func in subcommands:
        # XXX: how to extract short subcommand docstrings?
        fdoc = ""
        doc.append(fmt_str % (func.__name__, fdoc))

    master.__doc__ = "Usage: %prog COMMAND ...\n\n" + "\n".join(doc)

    return master

# Decorators
def notstrict(fn):
    fn.optfunc_notstrict = True
    return fn

def arghelp(name, help):
    def inner(fn):
        d = getattr(fn, 'optfunc_arghelp', {})
        d[name] = help
        setattr(fn, 'optfunc_arghelp', d)
        return fn
    return inner

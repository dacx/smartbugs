import os, importlib, json, argparse, multiprocessing
import src.output_parser.Parser as Parser

def reparser(taskqueue, output_parser, overwrite, verbose):
    fetched = 0
    skipped = 0
    while True:
        d = taskqueue.get()
        if d is None:
            break
        fetched += 1

        fn_log = f"{d}/result.log"
        fn_json = f"{d}/result.json"
        fn_jsonnew = f"{d}/result.new.json"
        if os.path.exists(fn_jsonnew) and not overwrite:
            skipped += 1
            if verbose:
                print(f"{fn_jsonnew} already exists, skipping")
            continue
        if verbose:
            print(d)
        result_json = Parser.reparse(output_parser, fn_log, fn_json)
        with open(fn_jsonnew, 'w') as f:
            print(json.dumps(result_json,indent=2), file=f)

    if verbose:
        print(f"{fetched} tasks fetched, {skipped} skipped")


def main():
    argparser = argparse.ArgumentParser(prog="python3 reparse.py", description="""
        Parse the tool output into files named 'result.new.json'.
        If 'result.json' exists, it is used to initialize 'result.new.json'.
        No parsing if 'result.new.json' already exists.
        """)
    argparser.add_argument("-f", "--overwrite", action='store_true', help="Overwrite result.new.json.")
    argparser.add_argument("-v", "--verbose", action='store_true', help="Document progress.")
    argparser.add_argument("--processes", type=int, metavar="N", default=1, help="number of parallel processes (default 1)")
    argparser.add_argument("path_to_output", help="directory containing the tool output")
    argparser.add_argument("parser_name", help="name of Python module for parsing the output")
    args = argparser.parse_args()

    overwrite = args.overwrite
    verbose = args.verbose
    processes = args.processes
    top = args.path_to_output
    parser_name = args.parser_name

    module = importlib.import_module(f"src.output_parser.{parser_name}")
    output_parser = getattr(module, parser_name)

    # spawn processes, instead of forking, to have same behavior under Linux and MacOS
    mp = multiprocessing.get_context("spawn")
    taskqueue = mp.Queue()

    reparsers = [ mp.Process(target=reparser, args=(taskqueue,output_parser,overwrite,verbose)) for _ in range(processes) ]
    for r in reparsers:
        r.start()

    for path,_,files in os.walk(top):
        for f in files:
            if f.startswith('result.'):
                taskqueue.put(path)
                break

    for _ in range(processes):
        taskqueue.put(None)

    for r in reparsers:
        r.join()



if __name__ == '__main__':
    main()

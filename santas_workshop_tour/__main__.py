import logging
import os
from datetime import datetime
import pandas as pd
from santas_workshop_tour.cli import MyArgumentParser, MappingAction
from santas_workshop_tour.clonator import BasicClonator
from santas_workshop_tour.mutator import BasicMutator, PreferenceMutator, \
    AdvancedPreferenceMutator
from santas_workshop_tour.selector import BasicSelector, \
    PercentileAffinitySelector
from santas_workshop_tour.artificial_immune_system import \
    ArtificialImmuneSystem

logging_level_mapping = {
    'critical': logging.CRITICAL,
    'error': logging.ERROR,
    'warning': logging.WARNING,
    'info': logging.INFO,
    'debug': logging.DEBUG
}
clonator_mapping = {
    'basic': BasicClonator,
}
mutator_mapping = {
    'basic': BasicMutator,
    'preference': PreferenceMutator,
    'advanced_preference': AdvancedPreferenceMutator
}
selector_mapping = {
    'basic': BasicSelector,
    'percentile': PercentileAffinitySelector
}


def main(args):
    """
    Main execution function.

    :param args: dict, argparse arguments.
    """
    # Create logger for santas_workshop_tour package
    logger = logging.getLogger('santas_workshop_tour')
    logger.setLevel(args.logging_level)

    # Create console handler
    ch = logging.StreamHandler()
    ch.setLevel(args.logging_level)

    # Create file handler
    if not os.path.isdir(args.output_directory):
        os.makedirs(args.output_directory)
    now = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    log_file_path = os.path.join(
        args.output_directory,
        f'logs_{now}.out'
    )
    fh = logging.FileHandler(log_file_path, mode='w')
    fh.setLevel(logging.DEBUG)

    # Create formatter and add it to the handlers
    fmt = '%(asctime)-15s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(fmt=fmt, datefmt='%Y-%m-%d %H:%M:%S')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    # Run artificial immune system optimization
    ais = ArtificialImmuneSystem(
        df_families=pd.read_csv(args.data_file_path),
        clonator=args.clonator(),
        mutator=args.mutator(),
        selector=args.selector(
            affinity_threshold=args.affinity_threshold,
            select_type=args.select_type
        ),
        population_size=args.population_size,
        n_generations=args.n_generations,
        n_cpu=args.n_cpu,
        interactive_plot=args.interactive_plot,
        output_directory=args.output_directory
    )
    ais.optimize()


if __name__ == '__main__':
    parser = MyArgumentParser(
        prog='santas_workshop_tour',
        description="Program to solve the Santa's Workshop Tour 2019 problem.",
        fromfile_prefix_chars='@'
    )

    # Required named arguments
    parser_required_named = parser.add_argument_group(
        'required named arguments'
    )
    parser_required_named.add_argument(
        '--data-file-path',
        required=True,
        type=str,
        help='Path to the data to be optimized.'
    )

    # Cloning algorithm required named arguments
    parser_clonator_required_named = parser.add_argument_group(
        'cloning algorithm required named arguments'
    )
    parser_clonator_required_named.add_argument(
        '--clonator',
        action=MappingAction,
        mapping=clonator_mapping,
        help='Cloning algorithm to be used.'
    )

    # Mutation algorithm required named arguments
    parser_mutator_required_named = parser.add_argument_group(
        'mutation algorithm required named arguments'
    )
    parser_mutator_required_named.add_argument(
        '--mutator',
        action=MappingAction,
        mapping=mutator_mapping,
        help='Mutation algorithm to be used.'
    )

    # Selection algorithm required named arguments
    parser_selector_required_named = parser.add_argument_group(
        'selection algorithm required named arguments'
    )
    parser_selector_required_named.add_argument(
        '--selector',
        action=MappingAction,
        mapping=selector_mapping,
        help='Selection algorithm to be used.'
    )
    parser_selector_required_named.add_argument(
        '--affinity-threshold',
        required=True,
        type=int,
        help='Threshold according to which the selection is done.'
    )

    parser_selector_required_named.add_argument(
        '--select-type',
        required=True,
        type=str,
        help='Whether selection will be positive or negative.'
    )

    # Artificial Immune System algorithm required named arguments
    parser_ais_required_named = parser.add_argument_group(
        'artificial immune system algorithm required named arguments'
    )
    parser_ais_required_named.add_argument(
        '--population-size',
        required=True,
        type=int,
        help='Size of population.'
    )
    parser_ais_required_named.add_argument(
        '--n-generations',
        required=True,
        type=int,
        help='Number of generations.'
    )

    # Optional arguments
    parser.add_argument(
        '--logging-level',
        required=False,
        action=MappingAction,
        mapping=logging_level_mapping,
        default='info',
        help='Logging level (default: %(default)s).'
    )
    parser.add_argument(
        '--n-cpu',
        type=int,
        default=1,
        help='Number of CPU to be used (default: %(default)s).'
    )
    parser.add_argument(
        '--interactive-plot',
        action='store_true',
        default=False,
        help='Whether plot is rendering during optimization (default: '
             '%(default)s).'
    )
    parser.add_argument(
        '--output-directory',
        type=str,
        default='output',
        help='Directory where output files (plot, best solution and '
             'logs) will be saved (default: %(default)s).'
    )

    main(parser.parse_args())

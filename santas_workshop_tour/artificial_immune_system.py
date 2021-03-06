import logging
import multiprocessing
import os
from datetime import datetime
from functools import partial
import pandas as pd
import matplotlib.pyplot as plt
from santas_workshop_tour.antibody import Antibody


class ArtificialImmuneSystem:
    """
    Class representing Artificial Immune System algorithm.

    :param df_families: pandas.DataFrame, contains size and
        preferences of all families. Data to be optimized.
    :param clonator: Clonator, object to perform cloning.
    :param mutator: Mutator, object to perform mutations.
    :param selector: Selector, object to perform selection.
    :param population_size: int, size of population.
    :param n_generations: int, number of generations.
    :param n_cpu: int (default: 1), number of CPU to be used.
    :param interactive_plot: bool (default: False), whether plot is
        rendering during optimization.
    :param output_directory: str (default: output), directory where
        output files (plot and best solution) will be saved.
    """

    def __init__(
        self,
        df_families,
        clonator,
        mutator,
        selector,
        population_size,
        n_generations,
        n_cpu=1,
        interactive_plot=False,
        output_directory='output'
    ):
        """
        Create a new object of class `ArtificialImmuneSystem`.

        :param df_families: pandas.DataFrame, contains size and
            preferences of all families. Data to be optimized.
        :param clonator: Clonator, object to perform cloning.
        :param mutator: Mutator, object to perform mutations.
        :param selector: Selector, object to perform selection.
        :param population_size: int, size of population.
        :param n_generations: int, number of generations.
        :param n_cpu: int (default: 1), number of CPU to be used.
        :param interactive_plot: bool (default: False), whether plot is
            rendering during optimization.
        :param output_directory: str (default: output), directory where
            output files (plot and best solution) will be saved.
        """
        self.df_families = df_families
        self.clonator = clonator
        self.mutator = mutator
        self.selector = selector
        self.population_size = population_size
        self.n_generations = n_generations
        self.n_cpu = n_cpu
        self.interactive_plot = interactive_plot
        self.output_directory = output_directory
        self._logger = logging.getLogger(__name__) \
            .getChild(self.__class__.__name__)

        # Create axes for plotting
        plt.figure(figsize=(15, 8))
        self._ax_min_fitness = plt.subplot(1, 2, 1)
        plt.xlabel('Generation')
        plt.ylabel('Min fitness value')
        self._ax_avg_fitness = plt.subplot(1, 2, 2)
        plt.xlabel('Generation')
        plt.ylabel('Avg fitness value')

        # Helper variables for plotting
        self._prev_generation = None
        self._prev_min_fitness = None
        self._prev_avg_fitness = None

    def generate_population(self, n=None):
        """
        Generate random population of antibodies of size
        `self.population_size`.

        :param n: int (default: None), size of population to be
            generated. If `None` then population of size
            `self.population_size` will be generated.
        :return: list, list of `Antibody` object.
        """
        n = self.population_size if n is None else n
        population = []
        with multiprocessing.Pool(self.n_cpu) as pool:
            for _ in range(n):
                pool.apply_async(
                    Antibody().generate_solution,
                    args=[self.df_families],
                    callback=lambda x: population.append(x)
                )
            pool.close()
            pool.join()

        return population

    @staticmethod
    def affinity(population):
        """
        Compute affinity between each antibody in `population`.

        Before calculation of affinity affinity values of all members of
        population are reset to 0 to prevent transfer of affinity across
        generations.
        :param population: list, list of `Antibody` objects.
        :return: float, average affinity value.
        """
        for member in population:
            member.affinity_value = 0

        affinity_sum = 0
        for i, a1 in enumerate(population):
            for a2 in population[i + 1:]:
                affinity = a1.affinity(a2)
                a1.affinity_value += affinity
                a2.affinity_value += affinity
                affinity_sum += (2 * affinity)
        return affinity_sum / len(population)

    @staticmethod
    def _fitness(antibody, df_families=None):
        """
        Compute fitness of given `antibody`.

        Helper method for parallel computation.

        :param antibody: Antibody, antibody to be fitness computed for.
        :param df_families: pandas.DataFrame, contains size and
            preferences of all families. Data to be optimized.
        """
        return antibody.fitness(df_families)

    def fitness(self, population):
        """
        Compute fitness of each antibody in `population`.

        :param population: list, list of `Antibody` objects.
        :return:
            list, list of antibodies with calculated fitness values.
            Antibody, antibody with minimum fitness value.
            float, average fitness value.
        """
        sum_fitness = 0
        best_antibody = Antibody()
        best_antibody.fitness_value = 999999999999

        with multiprocessing.Pool(self.n_cpu) as pool:
            fn = partial(self._fitness, df_families=self.df_families)
            population = pool.map(fn, population)

        for antibody in population:
            sum_fitness += antibody.fitness_value
            if antibody.fitness_value < best_antibody.fitness_value:
                best_antibody = antibody

        return population, best_antibody, sum_fitness / len(population)

    # TODO: add test
    def fitness_clones(self, clones):
        """
        Compute fitness of each clone in `clones`.

        For utilization of parallel computing, clones are flatten to 1D
        list before fitness computation and then are recreated with
        right shape.

        :param clones: list, list of list of `Antibody` objects.
        :return: list, list of list of `Antibody` objects.
        """
        sizes, aux_clones = [], []

        # Flat clones to 1D list
        for list_of_clones in clones:
            for clone in list_of_clones:
                aux_clones.append(clone)
            sizes.append(len(list_of_clones))

        # Compute fitness in parallel
        aux_clones, _, _ = self.fitness(aux_clones)

        # Recreate clones with right shape
        clones, start = [], 0
        for size in sizes:
            end = start + size
            clones.append(aux_clones[start:end])
            start = end

        return clones

    def select_best(self, population, clones):
        """
        Select best antibodies from population and clones.

        i-th best antibody is one whose fitness is the lowest among i-th
        antibody in `population` and its corresponding i-th `clones`.

        :param population: list, list of `Antibody` objects.
        :param clones: list, list of list of `Antibody` objects.
        """
        new_population = []
        for antibody, list_of_clones in zip(population, clones):
            best_clone = min(list_of_clones)
            new_population.append(
                best_clone if best_clone < antibody else antibody
            )
        return new_population

    def optimize(self):
        """
        Artificial Immune System optimization.

        Optimize solution for data in `self.df_families`.
        """
        best_antibody = None

        # Initialization
        self._logger.info('Initial population generation')
        population = self.generate_population()
        self._logger.debug('Affinity computation')
        self.affinity(population)

        # Optimization loop
        for i in range(self.n_generations):
            self._logger.info(f'Generation {i+1}')
            self._logger.debug('Fitness computation')
            population, best_antibody, avg_fitness = self.fitness(population)

            self._logger.debug('Cloning')
            clones = self.clonator.clone(population)

            self._logger.debug('Mutating')
            clones = self.mutator.mutate(
                clones,
                self.df_families
            )

            self._logger.debug('Clones fitness computation')
            clones = self.fitness_clones(clones)

            self._logger.debug(
                f'Best antibody from population and clones selection'
            )
            population = self.select_best(population, clones)

            self._logger.debug('Affinity computation')
            avg_affinity = self.affinity(population)

            self._logger.debug('Selecting')
            population = self.selector.select(population)
            self._logger.debug(
                f'Population size after selection {len(population)}'
            )

            n = self.population_size - len(population)
            if n > 0:
                self._logger.debug('New antibodies generation')
                population.extend(self.generate_population(n=n))

            self._logger.info(
                f'Min fitness: {best_antibody.fitness_value}, '
                f'Avg fitness: {avg_fitness}, '
                f'Avg affinity: {avg_affinity}'
                '\n'
            )
            self.plot(i + 1, best_antibody.fitness_value, avg_fitness)

        if best_antibody is not None:
            self.save_output(best_antibody)

    def plot(self, generation, min_fitness, avg_fitness):
        """
        Plot progress of min and avg fitness.

        :param generation: int, generation number.
        :param min_fitness: float, fitness value of the best antibody.
        :param avg_fitness: float, average fitness value of all
            antibodies.
        """
        # Set initial values
        self._prev_generation = generation if \
            self._prev_generation is None else self._prev_generation
        self._prev_min_fitness = min_fitness \
            if self._prev_min_fitness is None else self._prev_min_fitness
        self._prev_avg_fitness = avg_fitness \
            if self._prev_avg_fitness is None else self._prev_avg_fitness

        # Plot values
        self._ax_min_fitness.plot(
            [self._prev_generation, generation],
            [self._prev_min_fitness, min_fitness],
            'bo-'
        )
        self._ax_avg_fitness.plot(
            [self._prev_generation, generation],
            [self._prev_avg_fitness, avg_fitness],
            'bo-'
        )
        if self.interactive_plot:
            plt.pause(0.000001)

        # Update previous values
        self._prev_generation = generation
        self._prev_min_fitness = min_fitness
        self._prev_avg_fitness = avg_fitness

    def save_output(self, antibody):
        """
        Save solution and plot figure.

        :param antibody: Antibody, antibody to be saved as a solution.
        """
        if not os.path.isdir(self.output_directory):
            os.makedirs(self.output_directory)
        now = datetime.now().strftime('%Y-%m-%d-%H%M%S')

        # Save best solution
        solution_path = os.path.join(
            self.output_directory,
            f'solution_{now}.csv'
        )
        solution_df = pd.DataFrame({
            'family_id': [i for i in range(len(antibody.families))],
            'assigned_id': antibody.families
        })
        solution_df.to_csv(solution_path, index=False)
        self._logger.info(f'Solution was saved to {solution_path}')

        # Save plot
        plot_path = os.path.join(
            self.output_directory,
            f'plot_{now}.pdf'
        )
        plt.savefig(plot_path)
        self._logger.info(f'Plot was saved to {plot_path}')

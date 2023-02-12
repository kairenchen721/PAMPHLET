import matplotlib.pyplot as plt
from typing import List, Dict, Set, Tuple, Union

from temp import write_output

"""the only 0th level function in this file"""


def choose_probe_placement(
        gene_mutation_type_info_dict: Dict[str, dict],
        targeting_window_size: int = 80,
        cumulative_contribution_threshold: int = 90,
        indel_filter_threshold: int = 30, recurrent_definition: int = 2):
    """
    Choose probe using one of two approach, generate all probe then greedily choose
    the most recurrent one (the set cover greedy algorithm approach), \
    rank all mutations based on recurrent-ness then add all mutation within the
    targeting window centered around that mutation
    :param gene_mutation_type_info_dict: A dictionary mapping gene to info
    :param targeting_window_size: see user_chose_options
    :param cumulative_contribution_threshold: see user_chose_options
    :param indel_filter_threshold: see user_chose_options
    :param recurrent_definition: see user_chose_options
    """

    # mutation_list = rank_all_probe_choose_most_recurrent(
    #     gene_mutation_type_info_dict, cumulative_contribution_threshold,
    #     targeting_window_size,
    #     indel_filter_threshold, recurrent_definition)

    mutation_list = chose_most_recurrent_mutation_then_probe_centered_at_mutation_center(
        gene_mutation_type_info_dict, cumulative_contribution_threshold,
        targeting_window_size,
        indel_filter_threshold, recurrent_definition)

    # [position_most_tumour, cumulative_contribution, first_mutation_in_probe,
    #   last_mutation_in_probe, tumour_set_selected_position_and_probe])

    for probe in mutation_list:
        print(probe)

    write_output(mutation_list, 'probe.xlsx')


"""1st level function"""
"""the choose most recurrent mutation and centered approach"""


def chose_most_recurrent_mutation_then_probe_centered_at_mutation_center(
        gene_info_dict: Dict[str, dict], cumulative_contribution_threshold: int,
        targeting_window_size: int,
        indel_filter_threshold: int, recurrent_definition: int) -> list:
    """
    This approach choose the most recurrent mutation based on number of
    tumour that has this mutation (the greater the number of tumour, the more
    recurrent it is), and then these covered tumour are removed from every other
    mutation's list, so that all other mutation can be ranked by the number of
    tumours they have in addition to the ones already covered. Due to that, the already selected
    mutation will have number of tumours of zero. Additionally, for each selected
    mutation, it will attempt to see if any other mutation can be covered
    by the targeting window whose center is the center of the selected mutation.
    Repeat until total number of tumour covered by the selected mutation and
    its targeting window exceeds the cumulative contribution threshold, which
    is a percentage of the total number of unique recurrent tumours
    :param gene_info_dict: A dictionary mapping gene to info
    :param cumulative_contribution_threshold: see user_chose_options
    :param targeting_window_size: see user_chose_options
    :param indel_filter_threshold: see user_chose_options
    :param recurrent_definition: see user_chose_options
    :return: A list of probe, with two genomic location, indicating the
    5' most mutation and the 3' most mutation of that probe, and the cumulative
    contribution up to and including that probe.
    """
    all_tumour_id = []
    gene_tumour_position = {}

    # group tumour id based on genomic position
    get_mapping_position_tumour(all_tumour_id, gene_tumour_position,
                                gene_info_dict,
                                indel_filter_threshold)

    # each gene has one dict holding position mapping to tumour
    # and another mapping position with deletion to tumour
    # combine them two
    all_position_tumour_dict = {}
    all_position_tumour_dict_deletion = {}
    for gene, position_tumour_dict_list in gene_tumour_position.items():

        position_tumour = position_tumour_dict_list[0]
        position_tumour_deletion = position_tumour_dict_list[2]

        for position, tumour_set in position_tumour.items():
            all_position_tumour_dict[position] = set(tumour_set)

        for deletion, tumour_set in position_tumour_deletion.items():
            all_position_tumour_dict[deletion] = set(tumour_set)
            all_position_tumour_dict_deletion[deletion] = set(tumour_set)

    tumour_set_list = []
    unique_tumour_id = []
    recurrent_unique_tumour_id = count_mutation_and_tumour_after_filters(
        gene_tumour_position, recurrent_definition, tumour_set_list,
        unique_tumour_id)

    # center_probe_dict = all_position_tumour_dict.copy()

    print('start finding cover')
    covered_tumour_id = []
    cover_sizes_percentage = [0]
    percentage_cover_threshold = len(
        recurrent_unique_tumour_id) * cumulative_contribution_threshold / 100
    mutation_list = []
    find_probe_cover(all_position_tumour_dict, cover_sizes_percentage,
                     covered_tumour_id, mutation_list,
                     percentage_cover_threshold, recurrent_definition,
                     recurrent_unique_tumour_id, targeting_window_size,
                     all_position_tumour_dict_deletion)

    # print('start centering probes')
    # final_mutation_list = []
    # centralize_each_probe(center_probe_dict, final_mutation_list, mutation_list,
    #                       recurrent_definition, targeting_window_size)

    plt.plot(cover_sizes_percentage, linewidth=1)
    plt.ylabel('percentage of tumour covered')
    plt.xlabel('number of ' + str(targeting_window_size) + 'bp probes selected')
    plt.title('coverage of tumours with increasing probe ')
    plt.savefig('stop_at_90.pdf')

    return mutation_list


"""1st level function"""
"""the set cover greedy approach"""


def rank_all_probe_choose_most_recurrent(
        gene_info_dict: Dict[str, dict], cumulative_contribution_threshold: int,
        targeting_window_size: int,
        indel_filter_threshold: int, recurrent_definition: int) -> List[list]:
    """
    so this is actually a set cover problem, whose naive greedy algorithm produces
    a solution with the upper bound of OPT log_e n where OPT is the optimal
    solution and the n the total number of element (size of the universe)
    our unique n = 35566 , so the optimal solution is at most 11 times smaller
    there is faster greedy algorithms, see wikipedia or CLRS
    the number of sets is 9915
    there is a 9:5073770 with 17333

    since we are trying to cover mutation with a probe of 100 bp, so we \
    changing the subset's definition to from 'all unique tumours at a bp' to \
    all unique tumour within a 80bp window' this mean we increase the subset size \
    now the approximation ratio does not change since it depend on universe size, \
    which has not changed, but the optimal solution has become smaller, how much smaller? \
    I don't know, not sure if it has to do with the fact that we don't know the \
    optimal solution to begin with

    To summarize, this approach generate all possible probe (with a user defined
    targeting window), by start from the 5' most of every gene, and shifting one
    base pair right each time (and each is a different possible probe), and then
    each probe corresponds to a set of tumours that have mutation within the limit
    of each probe. Finally, all probes are ranked by their number of tumour, and
    the probe with the most amount of tumours is selected first, then those
    tumours are removed from the set of every other probe. This is repeated until
    the number of tumours covered exceeds the cumulative contribution threshold
    :param gene_info_dict: A dictionary mapping gene to info
    :param cumulative_contribution_threshold: see user_chose_options
    :param targeting_window_size: see user_chose_options
    :param indel_filter_threshold: see user_chose_options
    :param recurrent_definition: see user_chose_options
    :return: A list of probe, with two genomic location, indicating the
    5' most mutation and the 3' most mutation of that probe, and the cumulative
    contribution up to and including that probe.
    """

    all_tumour_id = []
    gene_tumour_position = {}

    # group tumour id based on genomic position
    get_mapping_position_tumour(all_tumour_id, gene_tumour_position,
                                gene_info_dict,
                                indel_filter_threshold)

    all_possible_probe_tumour_dict = {}
    find_all_potential_probe_placement(gene_tumour_position,
                                       all_possible_probe_tumour_dict,
                                       recurrent_definition,
                                       targeting_window_size)

    tumour_set_list = []
    unique_tumour_id = []
    recurrent_unique_tumour_id = count_mutation_and_tumour_after_filters(
        gene_tumour_position, recurrent_definition, tumour_set_list,
        unique_tumour_id)

    print('total number of possible probes',
          len(all_possible_probe_tumour_dict))

    print('start finding cover')
    covered_tumour_id = []
    cover_sizes_percentage = [0]
    percentage_cover_threshold = len(
        recurrent_unique_tumour_id) * cumulative_contribution_threshold / 100
    probe_list = []

    find_probe_cover_greedy(all_possible_probe_tumour_dict,
                            cover_sizes_percentage, covered_tumour_id,
                            percentage_cover_threshold, probe_list,
                            recurrent_unique_tumour_id)

    plt.plot(cover_sizes_percentage, linewidth=1)
    plt.ylabel('percentage of tumour covered')
    plt.xlabel('number of ' + str(targeting_window_size) + 'bp probes selected')
    plt.title('coverage of tumours with increasing probe ')
    plt.savefig('stop_at_90.pdf')

    return [percentage_cover_threshold, probe_list, cover_sizes_percentage]


def find_all_potential_probe_placement(
        gene_tumour_position: Dict[str, List[Dict]],
        all_possible_probe_tumour_dict: Dict[str, Tuple[set, int, int]],
        recurrent_definition: int,
        targeting_window_size: int):
    """
    For each gene, generate all potential/possible probe, that is
    :param gene_tumour_position: A dictionary consist of gene mapping to a list
    of dictionaries, one of those dictionary maps position to tumour set, another
    one is maps position range of deletion mutation to tumour set
    :param all_possible_probe_tumour_dict: A dict to be populated of probes mapping
    to tumour sets
    :param recurrent_definition: see user_chose_options
    :param targeting_window_size: see user_chose_options
    """
    # TODO check if all deletion have all possible probes generated too
    counter = 1
    for gene_cell_type, position_tumour_dict_list in gene_tumour_position.items():

        position_tumour = position_tumour_dict_list[0]
        position_range_tumour_deletion = position_tumour_dict_list[2]

        # make a list of all position with mutation, sorted to be use in the next section
        all_position_list = []
        for position, tumour in position_tumour.items():
            all_position_list.append(position)
        all_position_list.sort()

        # make a list that denotes the number of unique tumour at all position
        # with or without mutation
        position_tumour_set_list = []
        all_position_list_with_gap = []
        position_num_tumour_list = []
        position_tumour_deletion_dict = {}
        make_position_info_list(position_tumour, position_range_tumour_deletion,
                                all_position_list,
                                all_position_list_with_gap,
                                position_num_tumour_list,
                                position_tumour_set_list,
                                position_tumour_deletion_dict)

        index_of_mutation = []
        for i in range(len(position_num_tumour_list)):
            # only if the mutation is recurrent, add it in
            if position_num_tumour_list[i] >= recurrent_definition:
                index_of_mutation.append(i)

        # calculate what tumour will be in each probe
        # another list to signify the index where the mutation is
        #   not empty, so that we only include probes that are within 80bp of
        #   each side for every mutation
        probe_tumour_set = []
        make_each_probe(all_position_list_with_gap,
                        all_possible_probe_tumour_dict, index_of_mutation,
                        position_tumour_set_list, probe_tumour_set,
                        targeting_window_size, recurrent_definition,
                        position_range_tumour_deletion,
                        position_tumour_deletion_dict)

        # the position in all_possible_probe_tumour_dict represent the
        # start of a probe, unlike position_tumour dict

        print('nth gene', counter, len(gene_tumour_position))
        counter += 1


"""3rd level function"""


def make_position_info_list(position_tumour: Dict[str, List[str]],
                            position_range_tumour_deletion: Dict[
                                str, List[str]],
                            all_position_list: List[str],
                            all_position_list_with_gap: List[str],
                            position_num_tumour_list: List[int],
                            position_tumour_set_list: List[
                                Union[List[str], str]],
                            position_deletion_dict: Dict[str, str]):
    """
    go through the dictionaries and make lists that contain information on
    the tumour sets of each mutation, the size of each tumour set, the actual
    chromosome+position of each mutation. These three list are connected by
    mutation positions, and the relative position of each mutation relative
    to the leftmost position are embedding here through indices of each list,
    meaning that for every base that does not have mutations, there is something
    in the lists that represents those gaps
    :param position_tumour: A dict mapping mutation position to tumour set
    :param position_range_tumour_deletion: A dict mapping deletion mutation's position
     range to tumour set
    :param position_deletion_dict: A dict mapping a position to a position range
     for deletion mutations
    :param all_position_list: A list of all mutated positions (chromosome position range)
    :param all_position_list_with_gap: same as above except for every base between
     that does not have any mutation, there is an empty string
    :param position_num_tumour_list: A list of int representing the number of
    tumour at that position
    :param position_tumour_set_list: A list of string or a list of list of str
     representing the tumour at that position, if none, then just '0'
    """
    # i want a dictionary of all position of any deletion to empty string
    # I need the covered base pairs of the deletion
    make_position_deletion_dict(position_deletion_dict,
                                position_range_tumour_deletion)

    for i in range(len(all_position_list)):
        last_position = all_position_list[i]
        tumour_set = list(set(position_tumour[last_position]))

        position_tumour_set_list.append(tumour_set)

        position_num_tumour_list.append(len(tumour_set))

        all_position_list_with_gap.append(last_position)

        if len(all_position_list) == 1:
            break

        # if we have reach the end of the end, do not add gaps, because there
        # are not meant to be any
        if i + 1 == len(all_position_list):
            break

        # if there is a gap of X, append X 0s
        next_position = all_position_list[i + 1]
        gap_length = find_gap_length(next_position, last_position)

        gap_list = ['0' for _ in range(gap_length)]
        position_gap_list = ['' for _ in range(gap_length)]
        num_gap_list = [0] * gap_length

        # a list of tumour set for each position, except where there is
        # no tumour at that position, then it has a '0'
        position_tumour_set_list.extend(gap_list)
        position_num_tumour_list.extend(num_gap_list)
        all_position_list_with_gap.extend(position_gap_list)


"""4th level function"""


def find_gap_length(next_position: str, last_position: str) -> int:
    """
    find the number of bases between two mutations (not deletions), or
    the gap length
    :param next_position: One of the mutations
    :param last_position: The other mutation
    :return: A integer represent the gap length
    """
    next_position_list = next_position.split(':')
    last_position_list = last_position.split(':')
    next_position_wo_chromosome = next_position_list[1]
    last_position_wo_chromosome = last_position_list[1]
    return int(next_position_wo_chromosome) - int(
        last_position_wo_chromosome) - 1


""" 3rd level function"""


def make_each_probe(all_position_list_with_gap: List[str],
                    all_possible_probe_tumour_dict: Dict[
                        str, Tuple[set, int, int]],
                    indices_of_mutation: List[int],
                    position_tumour_set_list: List[Union[List[str], str]],
                    probe_tumour_set: List[set], targeting_window_size,
                    recurrent_definition,
                    position_range_tumour_deletion: Dict[str, List[str]],
                    position_deletion_dict: Dict[str, str]):
    """
    This function is called once for every gene.
    Start with a probe that is at the leftmost position of the gene but still
    covering a mutated position, so that the mutated position is rightmost on
    the probe, then begin to shift the window by one base at one time to the right,
    each time is a different probe. This ends when a probe is at the rightmost position
    of the gene, but still covering a mutated position
    :param all_position_list_with_gap: A list of all mutated positions
     (chromosome position range) except for every base between that does not
     have any mutation, there is an empty string
    :param all_possible_probe_tumour_dict:  A dict to be populated of probes mapping
     to tumour sets, the leftmost recurrent mutation, and the rightmost recurrent
     mutation
    :param indices_of_mutation: A list of indices representing the position of
     each mutation to the leftmost mutation
    :param position_tumour_set_list: A list of string or a list of list of str
     representing the tumour at that position, if none, then just '0'
    :param probe_tumour_set: A list of sets of tumour that each probe covers
    :param targeting_window_size: see user_chose_options
    :param recurrent_definition: see user_chose_options
    :param position_range_tumour_deletion: A dict mapping deletion mutation's position
     range to tumour set
    :param position_deletion_dict: A dict mapping a position to a position range
     for deletion mutations
    """
    for current_position in range(len(position_tumour_set_list)):

        # TODO the function below is the bottle neck (that it ran for so many times)
        # this alone is 1105.556s out of 1653.824s (18.4 min out of 27min)
        # the rest of make each probe is 221
        # it was called 969 million times, but the rest of make each probe is called only 3m times
        # we need pre-filter this to reduce bottleneck

        between, index_of_first_mutation_covered = is_current_position_a_probe_length_before_mutation(
            current_position, indices_of_mutation, targeting_window_size)

        # skip, if it is not zero and not between
        if current_position != 0 and not between:
            continue

        # the starting base pair of this probe
        probe_start_bp = all_position_list_with_gap[current_position]

        all_tumour_probe, first_recurrent_mutation_location, last_recurrent_mutation_location \
            = collect_probe_unique_tumours(current_position,
                                           position_tumour_set_list,
                                           targeting_window_size,
                                           recurrent_definition,
                                           position_range_tumour_deletion,
                                           position_deletion_dict,
                                           probe_start_bp)

        # TODO only need to extend them by the index with mutations
        # i need everything from the last all_tumour_probe
        # except the one from the first set

        # first_tumour_set = set(probe_gene_section[i])
        #
        # only_in_first = set(all_tumour_probe) - first_tumour_set

        all_possible_probe_tumour_dict[probe_start_bp] = (all_tumour_probe,
                                                          first_recurrent_mutation_location,
                                                          last_recurrent_mutation_location)
        probe_tumour_set.append(all_tumour_probe)


"""4th level function"""


def is_current_position_a_probe_length_before_mutation(current_position: int,
                                                       indices_of_mutation:
                                                       List[int],
                                                       targeting_window_size: int):
    """
    check if the current position is at most targeting_window_size before a
     mutation (any element of indices_of_mutation)
    :param current_position: the current position we are checking
    :param indices_of_mutation: A list of indices representing the position of
     each mutation to the leftmost mutation
    :param targeting_window_size: see user_chose_option
    :return: if it is indeed close enough, and then closest mutation
    """
    between = False
    index_of_first_mutation_covered = 0
    for j in range(len(indices_of_mutation)):
        a_mutation_position = indices_of_mutation[j]
        if a_mutation_position - targeting_window_size <= current_position <= a_mutation_position:
            between = True
            index_of_first_mutation_covered = j
            break
    return between, index_of_first_mutation_covered


def collect_probe_unique_tumours(current_position: int,
                                 position_tumour_set_list: List[
                                     Union[List[str], str]],
                                 targeting_window_size: int,
                                 recurrent_definition: int,
                                 position_range_tumour_deletion: Dict[
                                     str, List[str]],
                                 position_deletion_dict: Dict[str, str],
                                 probe_start_bp: str):
    """
    Record all unique tumour covered by the targeting window of this probe
    :param probe_start_bp: The starting base pair of the probe (not necessarily the same
    as the leftmost recurrent mutation)
    :param position_deletion_dict: A dict mapping a position to a position range
     for deletion mutations
    :param position_range_tumour_deletion: A dict mapping deletion mutation's position
     range to tumour set
    :param current_position: the starting position of this potential probe (not
     represented as chromosome + position, just the relative position to leftmost
     position
    :param position_tumour_set_list: a list of sets that have of tumours id of that position
    :param targeting_window_size: the number of base pair our probe can target
    :param recurrent_definition: the number of samples for a mutation to be considered a recurrent mutation
    count the unique tumours that is covered by this potential probe
    """

    # the section of this gene that corresponds to this probe
    end_of_probe = current_position + targeting_window_size
    probe_gene_section = position_tumour_set_list[current_position:end_of_probe]
    # all unique tumour covered by this probe
    all_tumour_probe = []

    # if any base of the probe covers the deletion
    probe_end_bp = int(probe_start_bp) + targeting_window_size
    deletion_start_bp_list = []
    deletion_end_bp_list = []
    for i in range(int(probe_start_bp), probe_end_bp):
        # if this position is covered by one of the deletion
        if i in position_deletion_dict:
            deletion_position = position_deletion_dict[str(i)]
            # parse the chromosome position
            position_list, position_range_end, position_range_start, semicolon_index = parse_chromosome_position_range(
                deletion_position)
            # if yes, add its tumour to this probe
            if position_range_end < str(probe_end_bp):
                all_tumour_probe.extend(
                    position_range_tumour_deletion[deletion_position])

            deletion_start_bp_list.append(position_range_start)
            deletion_end_bp_list.append(position_range_end)

    deletion_start_bp_list = sorted(list(set(deletion_start_bp_list)))
    deletion_end_bp_list = sorted(list(set(deletion_end_bp_list)))

    position_counter = 0
    subin_location_list = []
    for tumour_set in probe_gene_section:
        position_counter += 1
        if tumour_set == '0':
            continue
        if len(tumour_set) < recurrent_definition:
            continue
        all_tumour_probe.extend(tumour_set)
        subin_location_list.append(position_counter)

    first_recurrent_mutation_location = min(subin_location_list[0],
                                            int(deletion_start_bp_list[0]))
    last_recurrent_mutation_location = max(subin_location_list[-1],
                                           int(deletion_end_bp_list[-1]))
    all_tumour_probe = set(all_tumour_probe)
    return all_tumour_probe, first_recurrent_mutation_location, last_recurrent_mutation_location


"""function used by both approach"""


# TODO refactor this, since it is pretty similar to finding cover greedy
def find_probe_cover(all_position_tumour_dict: Dict[str, Set[str]],
                     cover_sizes_percentage: List[float],
                     covered_tumour_id: List[str], mutation_list: List[
            Union[str, float, int, List[Union[str, List[str]]]]],
                     percentage_cover_threshold: float,
                     recurrent_definition: int,
                     recurrent_unique_tumour_id: List[str],
                     targeting_window_size: int,
                     all_position_tumour_dict_deletion: Dict[str, Set[str]]):
    """
    As long as it has not reached the cumulative contribution threshold,
    find position the currently has most tumour ids, then search in a targeting
    window centered around that position,
    :param all_position_tumour_dict: A dict mapping position to tumour set
    :param cover_sizes_percentage: The list of all cumulative contribution of
     each probe
    :param covered_tumour_id: The set of tumour id that is covered by this
     selection of mutation/probes
    :param mutation_list: A list of mutation/probe that contain all information
     about those probes (the position it starts at or central position), the
     cumulative contribution up to that probe, leftmost mutation in the probe,
     rightmost mutation in the probe, and the tumour set that it covers
    :param percentage_cover_threshold: The covered tumour ids of
     the selected probe should only stop after exceed this threshold. It is a
     percentage of recurrent_unique_tumour_id
    :param recurrent_definition: see user_chose_options
    :param recurrent_unique_tumour_id: The tumour ids that are unique and recurrent
    :param targeting_window_size: see user_chose_options
    :param all_position_tumour_dict_deletion: same as all_position_tumour_dict,
     but only with deletions
    :return:
    """
    while len(covered_tumour_id) < percentage_cover_threshold:

        # find the position that currently has the most tumour ids
        num_most_tumour = 0
        position_most_tumour = ''
        for position, tumour_set in all_position_tumour_dict.items():
            tumour_list = list(tumour_set)
            if len(tumour_list) > num_most_tumour:
                num_most_tumour = len(tumour_list)
                position_most_tumour = position

        # over the iteration, some tumour set will be empty, that is because
        # the tumour ids that are already covered is removed.

        # get the 5' most and the 3' most position in the probe, and the tumour
        # set that is covered by this probe
        first_mutation_selected_position_and_probe,\
        last_mutation_selected_position_and_probe,\
        tumour_set_selected_position_and_probe,\
        chromosome = get_probe_covered_tumours(
            all_position_tumour_dict, position_most_tumour,
            recurrent_definition, targeting_window_size,
            all_position_tumour_dict_deletion)

        first_mutation_in_probe = chromosome + ':' + str(first_mutation_selected_position_and_probe)
        last_mutation_in_probe = chromosome + ':' + str(last_mutation_selected_position_and_probe)

        # add the newly covered tumour ids, and keep it unique
        covered_tumour_id.extend(
            list(set(tumour_set_selected_position_and_probe)))
        covered_tumour_id = list(set(covered_tumour_id))
        # calculate new cumulative contribution
        cumulative_contribution = len(covered_tumour_id) / len(
            recurrent_unique_tumour_id)

        # position most tumour is represented by its central base pair
        mutation_list.append([position_most_tumour, cumulative_contribution,
                              first_mutation_in_probe,
                              last_mutation_in_probe,
                              tumour_set_selected_position_and_probe])
        cover_sizes_percentage.append(cumulative_contribution)
        print(cumulative_contribution)

        # for all set, remove tumour ids that is in current
        for position, tumour_set in all_position_tumour_dict.items():
            tumour_set = set(tumour_set)
            all_position_tumour_dict[position] = tumour_set.difference(
                tumour_set_selected_position_and_probe)


# TODO, do docstring for this, I forgot this last time
def get_probe_covered_tumours(all_position_tumour_dict: Dict[str, Set[str]],
                              position_most_tumour: str,
                              recurrent_definition: int,
                              targeting_window_size: int,
                              all_position_tumour_dict_deletion: Dict[str, Set[str]]) \
        -> Tuple[int, int, List[str], str]:
    # get its tumour set
    tumour_set_selected_position = all_position_tumour_dict[
        position_most_tumour]

    # get center of the mutation, then start search within the window size, where the center is
    # that center of mutation
    position_list, deletion_range_end, deletion_range_start, semicolon_index = parse_chromosome_position_range(
        position_most_tumour)
    mutation_center = (int(deletion_range_start) + int(deletion_range_end)) // 2
    probe_start = mutation_center - (targeting_window_size // 2)
    probe_end = mutation_center + (targeting_window_size // 2)

    tumour_set_selected_position_and_probe = []
    tumour_set_selected_position_and_probe.extend(tumour_set_selected_position)
    all_position_in_probe = []
    chromosome = position_most_tumour[:semicolon_index]
    # for every position from probe start to probe end, which is centered
    # around the center of the chosen recurrent position
    for i in range(probe_start, probe_end):

        a_position_in_probe = i
        position_in_genome = chromosome + ':' + str(a_position_in_probe)

        # get it from non-deletions
        a_position_in_probe_tumour_set = all_position_tumour_dict.get(
            position_in_genome)

        # if a position is mutated, and is recurrent
        if a_position_in_probe_tumour_set is not None and len(
                a_position_in_probe_tumour_set) >= recurrent_definition:

            # add its tumour set to the tumour set that probe covers
            tumour_set_selected_position_and_probe.extend(
                a_position_in_probe_tumour_set)
            all_position_in_probe.append(a_position_in_probe)

        # TODO: move making dict outside, I doing the same thing multiple times
        # then get it from deletions
        # first creating a mapping from chromosome position to a deletion
        chromosome_position_deletion_dict = {}
        make_chromosome_position_deletion(all_position_tumour_dict_deletion, chromosome_position_deletion_dict,)

        # see which deletion does this position belong to
        the_deletion_range = chromosome_position_deletion_dict.get(position_in_genome)

        # if the position belong to a deletion
        if the_deletion_range is not None:
            # get the deletion's tumour set
            a_position_in_probe_tumour_set_deletion = all_position_tumour_dict_deletion.get(
                the_deletion_range)
            # it should be mutated but check again and if it is recurrent
            if a_position_in_probe_tumour_set_deletion is not None and len(
                    a_position_in_probe_tumour_set_deletion) >= recurrent_definition:
                # add its tumour set to the tumour set that probe covers
                tumour_set_selected_position_and_probe.extend(
                    a_position_in_probe_tumour_set_deletion)
                position_list, deletion_range_end, deletion_range_start, semicolon_index\
                    = parse_chromosome_position_range(the_deletion_range)
                all_position_in_probe.append(int(deletion_range_start))
                all_position_in_probe.append(int(deletion_range_end))

    all_position_in_probe.sort()
    # now one before
    first_mutation_selected_position_and_probe = all_position_in_probe[0] - 1
    last_mutation_selected_position_and_probe = all_position_in_probe[-1] + 1

    return first_mutation_selected_position_and_probe, last_mutation_selected_position_and_probe, tumour_set_selected_position_and_probe, chromosome


def make_chromosome_position_deletion(all_position_tumour_dict_deletion,
                                      chromosome_position_deletion_dict):
    """make a dictionary mapping chromosome position to chromosome position range"""
    for deletion_position_range, tumour_set in all_position_tumour_dict_deletion.items():
        position_list, position_range_end, position_range_start, semicolon_index = parse_chromosome_position_range(
            deletion_position_range)
        chromosome = deletion_position_range[:semicolon_index]
        for position in position_list:
            position_in_genome = chromosome + ':' + str(position)
            chromosome_position_deletion_dict[position_in_genome] = deletion_position_range


def find_probe_cover_greedy(all_possible_probe_tumour_dict,
                            cover_sizes_percentage, covered_tumour_id,
                            percentage_cover_threshold, probe_list,
                            recurrent_unique_tumour_id):
    while len(covered_tumour_id) < percentage_cover_threshold:

        # the tumour ids of the position that current has the most tumour ids
        num_most_tumour = 0
        probe_most_tumour = ''
        for probe, tumour_set in all_possible_probe_tumour_dict.items():
            if len(tumour_set[0]) > num_most_tumour:
                num_most_tumour = len(tumour_set[0])
                probe_most_tumour = probe
        tumour_set_selected_probe = all_possible_probe_tumour_dict[
            probe_most_tumour][0]
        first_mutation_selected_probe = all_possible_probe_tumour_dict[
            probe_most_tumour][1]
        last_mutation_selected_probe = all_possible_probe_tumour_dict[
            probe_most_tumour][2]
        all_possible_probe_tumour_dict.pop(probe_most_tumour, None)

        # TODO:
        # print first_mutation_selected_probe
        # and see if you can add one base pair to it

        # add the newly covered tumour ids, and keep it unique
        covered_tumour_id.extend(list(tumour_set_selected_probe))
        covered_tumour_id = list(set(covered_tumour_id))
        # calculate new cumulative contribution
        cumulative_contribution = len(covered_tumour_id) / len(
            recurrent_unique_tumour_id)

        # probe most tumour is represented by its starting base pair
        probe_list.append([probe_most_tumour, cumulative_contribution,
                           first_mutation_selected_probe,
                           last_mutation_selected_probe])
        cover_sizes_percentage.append(cumulative_contribution)
        print(cumulative_contribution)

        # for every other set, subtract tumour ids in current, add to new list
        for probe, tumour_set in all_possible_probe_tumour_dict.items():
            all_possible_probe_tumour_dict[probe][0] = tumour_set[0].difference(
                tumour_set_selected_probe)


def count_mutation_and_tumour_after_filters(
        gene_tumour_position: Dict[str, List[Dict[str, List[str]]]],
        recurrent_definition: int,
        tumour_set_list: List[List[str]], unique_tumour_id: List[str]):
    """
    # extract all sets of tumour, remove duplicates within each set, remove
    # duplicate set. that is convert to set for all 'subset', and convert to
    # multiset for all the collection of the subset remove duplicates and count
    # number of unique tumours this is to know the number of (recurrent) unique tumours
    :param gene_tumour_position: A dictionary mapping gene to a list of two
     other dictionaries, position tumour (a dict mapping position to tumour) and
     position_range_tumour_deletion (a dict mapping position_range to tumour set
     for deletion mutations)
    :param recurrent_definition: see user_chose_option
    :param tumour_set_list: A list of all tumour sets (so length of list is
     number of mutations)
    :param unique_tumour_id: A list of all unique tumour ids
    :return: All recurrent unique tumour id
    """
    for gene, position_tumour_dict_list in gene_tumour_position.items():
        position_tumour = position_tumour_dict_list[0]
        position_range_tumour_deletion = position_tumour_dict_list[2]

        # add tumours ids from deletion mutation
        for deletion, tumour_ids in position_range_tumour_deletion.items():
            tumour_ids_set = list(set(tumour_ids))
            tumour_set_list.append(tumour_ids_set)
            unique_tumour_id.extend(tumour_ids_set)

        # add tumours ids from other mutations
        for position, tumour_ids in position_tumour.items():
            tumour_ids_set = list(set(tumour_ids))
            tumour_set_list.append(tumour_ids_set)
            unique_tumour_id.extend(tumour_ids_set)

    unique_tumour_id = list(set(unique_tumour_id))
    # we now have
    # a dict with genomic position to a list of tumour ids and its reverse
    # a list of set of tumour ids
    # recurrent mutation here is a base pair that is mutated in multiple tumour
    # since each tumour set is a set a tumour that is mutated at that position
    # keep only recurrent mutations, means only using sets with >=2 tumour
    # which is the default recurrent definition
    recurrent_unique_tumour_set_list = [tumour_set
                                        for tumour_set in tumour_set_list
                                        if
                                        len(tumour_set) >= recurrent_definition]
    # then only keep these tumour ids
    recurrent_unique_tumour_id = list(set([tumour_id
                                           for tumour_set in
                                           recurrent_unique_tumour_set_list
                                           for tumour_id in tumour_set]))
    print('total number of mutations after indel filter',
          len(tumour_set_list))
    print('total number of tumours after indel filter',
          len(unique_tumour_id))
    print('total number of recurrent mutations after indel filter',
          len(recurrent_unique_tumour_set_list))
    print(
        'total number of tumours with only recurrent mutations after indel filter',
        len(recurrent_unique_tumour_id))
    return recurrent_unique_tumour_id


def parse_chromosome_position_range(chromosome_position_range: str):
    # example 2:3241-3276
    semicolon_index = chromosome_position_range.index(':')

    # this '8:30837618' is possible
    if '-' not in chromosome_position_range:
        position_range_start = chromosome_position_range[
                               semicolon_index + 1:]
        position_range_end = position_range_start
    else:
        dash_index = chromosome_position_range.index('-')
        position_range_start = chromosome_position_range[
                               semicolon_index + 1:dash_index]
        position_range_end = chromosome_position_range[dash_index + 1:]

    position_list = list(range(int(position_range_start),
                               int(position_range_end) + 1))
    return position_list, position_range_end, position_range_start, semicolon_index


def get_mapping_position_tumour(all_tumour_id: List[str],
                                gene_tumour_position: Dict[str, List[
                                    Dict[str, List[str]]]],
                                gene_mutation_type_info_dict: Dict[str, dict],
                                indel_filter_threshold: int):
    """
    Turn gene_mutation_type_info_dict's info which for every genes, there are and
    are multiple list and each element corresponds to one mutation, we want to make
    a new dictionary that maps position to tumour set.
    Also, we want to know how many mutation and tumour are there before after
    filtering indels
    :param all_tumour_id: All tumour id present in the file
    :param gene_tumour_position: A dictionary mapping gene to a list of two
     other dictionaries, position tumour (a dict mapping position to tumour) and
     position_range_tumour_deletion (a dict mapping position_range to tumour set
     for deletion mutations)
    :param gene_mutation_type_info_dict: maps gene name to info
    :param indel_filter_threshold: indels greater than this will be filter out
    :return:
    """

    all_tumour_id_before_indel_filter = []
    num_mutation_before_indel_filter = 0
    for gene_cell_type, info in gene_mutation_type_info_dict.items():

        for i in range(len(info['mutation genome position'])):
            tumour_id = info['id tumour'][i]
            all_tumour_id_before_indel_filter.append(tumour_id)

        num_mutation_before_indel_filter += len(
            info['mutation genome position'])

    all_tumour_id_before_indel_filter = list(
        set(all_tumour_id_before_indel_filter))

    print("total number of mutation before indel filter",
          num_mutation_before_indel_filter)
    print("total number of tumours before indel filter",
          len(all_tumour_id_before_indel_filter))

    for gene_cell_type, info in gene_mutation_type_info_dict.items():
        # assert len(info['mutation genome position']) == len(info['id tumour'])

        position_tumour = {}
        tumour_position = {}
        position_tumour_deletion = {}
        gene_tumour_position[gene_cell_type] = [position_tumour,
                                                tumour_position,
                                                position_tumour_deletion]
        for i in range(len(info['mutation genome position'])):
            chromosome_position_range = info['mutation genome position'][i]
            tumour_id = info['id tumour'][i]
            if chromosome_position_range != 'null' and tumour_id != 'null':

                # all genomic position are in the format a:b-c
                # where an is the chromosome number, followed by a semicolon
                # b is the start of the range, followed by a dash
                # c is the end of the range, followed by nothing
                # for single base pair mutation it is denoted as having the
                # same start and end of the range
                # for insertion, it is one more
                # deletion it is a lot more
                position_list, position_range_end, position_range_start, semicolon_index = parse_chromosome_position_range(
                    chromosome_position_range)

                # remove mutation with greater than then indel filter threshold (default is 30)
                if int(position_range_end) > int(
                        position_range_start) + indel_filter_threshold:
                    continue

                all_tumour_id.append(tumour_id)
                chromosome = chromosome_position_range[:semicolon_index]
                # if it is a deletion
                if int(position_range_end) > int(position_range_start) + 1:
                    position_tumour_deletion.setdefault(chromosome_position_range, []).append(
                        tumour_id)
                else:
                    for position in position_list:
                        chromosome_position = chromosome + ':' + str(position)
                        position_tumour.setdefault(chromosome_position, []).append(
                            tumour_id)
                        tumour_position.setdefault(tumour_id, []).append(
                            chromosome_position)


def make_position_deletion_dict(position_deletion_dict,
                                position_range_tumour_deletion):
    """
    :param position_deletion_dict: A dictionary mapping a position to a position
    range for deletion
    :param position_range_tumour_deletion: A dictionary mapping a position range
    to a list of tumour for deletion mutation
    :return:
    """
    for deletion_position_range, tumour_set in position_range_tumour_deletion.items():
        position_list, position_range_end, position_range_start, semicolon_index = parse_chromosome_position_range(
            deletion_position_range)
        for position in position_list:
            position_deletion_dict[position] = deletion_position_range


"""function not used anymore"""

# def centralize_each_probe(center_probe_dict, final_mutation_list, mutation_list,
#                           recurrent_definition, targeting_window_size):
#     # for each already selected probe
#     for probe in mutation_list:
#         probe_central_position = probe[0]
#         cumulative_contribution = probe[1]
#         tumour_set_selected_position_and_probe = probe[4]
#         num_tumour_covered_probe = len(tumour_set_selected_position_and_probe)
#         position_list, position_range_end, position_range_start, semicolon_index = parse_chromosome_position_range(
#             probe_central_position)
#
#         # each position is a center of a nearest-80-probes (if window size is
#         # at default, which is 80)
#         probe_start = probe_central_position - (targeting_window_size // 2)
#         probe_end = probe_central_position + (targeting_window_size // 2)
#
#         central_position_potential_probe_list = []
#
#         # a list of centrality of each probe, which is the average
#         # of the centrality of each position
#         potential_probe_centralities = []
#
#         chromosome = probe_central_position[:semicolon_index]
#
#         # for each potential probe
#         for i in range(probe_start, probe_end):
#
#             # a list of the centrality of each recurrent mutated position
#             probe_centrality_list = []
#
#             central_position_potential_probe = chromosome + ':' + str(
#                 i)
#             central_position_potential_probe_list.append(i)
#
#             first_mutation_centralized_position_and_probe, \
#             last_mutation_centralized_position_and_probe, \
#             tumour_set_centralized_position_and_probe \
#                 = get_probe_covered_tumours(
#                 center_probe_dict, central_position_potential_probe,
#                 recurrent_definition, targeting_window_size)
#
#             # find out the number of tumour set covered by this potential probe
#             num_tumour_covered_potential_probe = len(
#                 tumour_set_centralized_position_and_probe)
#
#             # if this potential probe does not lose information (has the
#             # same number of tumours, as the selected probe)
#             if num_tumour_covered_probe == num_tumour_covered_potential_probe:
#
#                 potential_probe_start = central_position_potential_probe - (
#                         targeting_window_size // 2)
#                 potential_probe_end = central_position_potential_probe + (
#                         targeting_window_size // 2)
#
#                 # for each mutation in each potential probe
#                 for j in range(potential_probe_start, potential_probe_end):
#                     a_position_potential_probe = j
#                     potential_probe_central_bp = chromosome + ':' + str(
#                         a_position_potential_probe)
#                     a_position_potential_probe_tumour_set = center_probe_dict.get(
#                         potential_probe_central_bp)
#                     # if this position has mutation and those mutations are recurrent (per user definition)
#                     if a_position_potential_probe_tumour_set is not None and \
#                             a_position_potential_probe_tumour_set >= recurrent_definition:
#                         # calculate the centrality of this position
#                         distance_from_central_position = abs(
#                             central_position_potential_probe - a_position_potential_probe)
#                         position_centrality = len(
#                             a_position_potential_probe_tumour_set) * distance_from_central_position
#                         probe_centrality_list.append(position_centrality)
#             # each potential probe has an average centrality
#             average_centrality = sum(probe_centrality_list) / len(
#                 probe_centrality_list)
#             potential_probe_centralities.append(average_centrality)
#
#         # Among all potential probe, find the probe with the lowest centrality,
#         # if there is a tie, choose the most 5' one
#         probe_lowest_centrality = [index for index, item in
#                                    enumerate(potential_probe_centralities) if
#                                    item == max(potential_probe_centralities)]
#         index_probe_lowest_centrality = probe_lowest_centrality[0]
#         # this would get me a position, I need to add the chromosome back into it
#         which_potential_probe = central_position_potential_probe_list[
#             index_probe_lowest_centrality]
#
#         # It has to be in on the same chromosome or else, this would not have chosen it
#         # this represents a probe, with its central base pair, after centralization is performed
#         # without losing information (not losing number of recurrent tumours covered
#         centralized_probe_position = chromosome + ':' + str(
#             which_potential_probe)
#
#         first_mutation_centralized_position_and_probe, \
#         last_mutation_centralized_position_and_probe, \
#         tumour_set_centralized_position_and_probe \
#             = get_probe_covered_tumours(
#             center_probe_dict, centralized_probe_position,
#             recurrent_definition, targeting_window_size)
#
#         # use this, find the first and last mutation of this probe
#
#         # TODO maybe the cumulative contribution is different?
#         #   if yes follow same steps as above
#
#         # generate new or keep old ones and add to final_mutation_list
#         final_mutation_list.append(
#             [probe_central_position, cumulative_contribution,
#              first_mutation_centralized_position_and_probe,
#              last_mutation_centralized_position_and_probe,
#              tumour_set_centralized_position_and_probe]
#         )

from dataclasses import dataclass
import logging as log
import os
import random
import _pylibfuzzer


@dataclass
class CorpusEntry:
    content: bytes
    fname: str
    origin: int
    depth: int
    hit_blocks: int = 0
    num_fuzzed: int = 0
    num_child: int = 0
    weight: float = 1
    burn_in: int = 5

    def compute_weight(self):
        self.weight = 1

        if self.burn_in:
            self.weight *= self.burn_in

    def __str__(self) -> str:
        return f"{self.fname}, depth={self.depth}, hit_blocks={self.hit_blocks}, num_fuzzed={self.num_fuzzed}, childs={self.num_child}, weight={self.weight}, burn_in={self.burn_in}"


class InputGeneration:
    def __init__(
        self,
        output_directory: str,
        seeds_directory: str | None = None,
        max_input_length: int = 15,
        libfuzzer_so_path: str | None = None,
    ):
        if libfuzzer_so_path is None:
            libfuzzer_so_path = os.path.join(
                os.path.dirname(__file__),
                "../dependencies/libFuzzerSrc/libfuzzer-mutator.so",
            )
            os.environ["libfuzzer_mutator_so_path"] = libfuzzer_so_path

        self.max_input_length = max_input_length

        self.corpus_directory = os.path.join(output_directory, "corpus")
        os.mkdir(self.corpus_directory)

        if not os.path.exists(libfuzzer_so_path):
            raise Exception(f"{libfuzzer_so_path=} does not exist.")

        if seeds_directory is not None:
            if not os.path.exists(seeds_directory):
                raise Exception(f"{seeds_directory=} does not exist.")

        self.corpus: list[CorpusEntry] = []
        self.current_base_input_index: int = -1
        self.retry_corpus_input_index: int = -1
        self.total_hit_blocks = 0

        if seeds_directory:
            self.add_seeds(seeds_directory)

        if len(self.corpus) == 0:
            self.add_corpus_entry(b"hi", 0, 0)

        _pylibfuzzer.initialize(max_input_length)

    def add_seeds(self, seeds_directory) -> None:
        for filename in sorted(os.listdir(seeds_directory)):
            file_path = os.path.join(seeds_directory, filename)

            if not os.path.isfile(file_path):
                continue
            with open(file_path, "rb") as f:
                seed = f.read()
                if len(seed) > self.max_input_length:
                    log.warning(
                        f"Seed {file_path=} was not added to the corpus "
                        f"because the seed length ({len(seed)}) was too large"
                        f" {self.max_input_length=}."
                    )
                    continue
                if seed not in self.corpus:
                    self.add_corpus_entry(seed, 0, 0)

    def add_corpus_entry(self, input: bytes, address: int, timestamp: int):
        file_path = os.path.join(
            self.corpus_directory,
            f"id:{str(len(self.corpus))},orig:{self.current_base_input_index},addr:{hex(address)},time:{timestamp}",
        )

        with open(file_path, "wb") as f:
            f.write(input)

        depth = 0

        if self.current_base_input_index >= 0:
            depth = self.corpus[self.current_base_input_index].depth + 1
            self.corpus[self.current_base_input_index].num_child += 1

        entry = CorpusEntry(input, file_path, self.current_base_input_index, depth)
        self.corpus.append(entry)

        return entry

    def choose_new_baseline_input(self):
        if self.retry_corpus_input_index > 0:
            self.retry_corpus_input_index = 0

        energy_sum = 0
        cum_energy = []

        for i in self.corpus:
            i.compute_weight()
            energy_sum += i.weight
            cum_energy.append(energy_sum)

        self.current_base_input_index = random.choices(
            range(len(self.corpus)), cum_weights=cum_energy
        ).pop()

        chosen_entry = self.corpus[self.current_base_input_index]
        chosen_entry.num_fuzzed += 1
        if chosen_entry.burn_in:
            chosen_entry.burn_in -= 1

    def get_baseline_input(self):
        return self.corpus[self.current_base_input_index].content

    def generate_input(self):
        if self.retry_corpus_input_index < len(self.corpus):
            input = self.corpus[self.retry_corpus_input_index].content
            self.retry_corpus_input_index += 1
            return input

        generate_input = _pylibfuzzer.mutate(
            self.corpus[self.current_base_input_index].content
        )

        return generate_input

    def report_address_reach(self, current_input: bytes, address: int, timestamp: int):
        self.total_hit_blocks += 1
        # log.info(f"saved to corpus {current_input}")
        for i in self.corpus:
            if i.content == current_input:
                i.hit_blocks += 1
                return

        self.retry_corpus_input_index = 0
        entry = self.add_corpus_entry(current_input, address, timestamp)

        entry.hit_blocks += 1

# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import subprocess
import time
from datetime import datetime

from openrelik_worker_common.utils import (
    count_lines_in_file,
    create_output_file,
    get_input_files,
    task_result,
)

from .app import celery

# Task name used to register and route the task to the correct queue.
TASK_NAME = "openrelik-worker-strings.tasks.strings"

# Task metadata for registration in the core system.
TASK_METADATA = {
    "display_name": "Strings",
    "description": "Extract strings from files",
}


@celery.task(bind=True, name=TASK_NAME, metadata=TASK_METADATA)
def strings(
    self,
    pipe_result: str = None,
    input_files: list = None,
    output_path: str = None,
    workflow_id: str = None,
    user_config: dict = None,
) -> str:
    """Extract ASCII strings from files.

    Args:
        pipe_result: Base64-encoded result from the previous Celery task, if any.
        input_files: List of input file dictionaries (unused if pipe_result exists).
        output_path: Path to the output directory.
        workflow_id: ID of the workflow.
        user_config: User configuration for the task (currently unused).

    Returns:
        Base64-encoded dictionary containing task results.
    """
    input_files = get_input_files(pipe_result, input_files or [])
    output_files = []
    base_command = ["strings", "-a", "-t", "d"]
    base_command_string = " ".join(base_command)

    for input_file in input_files:
        output_file = create_output_file(
            output_path,
            filename=input_file.get("filename"),
            file_extension="ascii_strings",
        )
        command = base_command + [input_file.get("path")]

        with open(output_file.path, "w") as fh:
            process = subprocess.Popen(command, stdout=fh)
            start_time = datetime.now()
            update_interval_s = 3

            while process.poll() is None:
                extracted_strings = count_lines_in_file(output_file.path)
                duration = datetime.now() - start_time
                rate = (
                    int(extracted_strings / duration.total_seconds())
                    if duration.total_seconds() > 0
                    else 0
                )
                self.send_event(
                    "task-progress",
                    data={"extracted_strings": extracted_strings, "rate": rate},
                )
                time.sleep(update_interval_s)

        output_files.append(output_file.to_dict())

    if not output_files:
        raise RuntimeError("No strings extracted from the provided files.")

    return task_result(
        output_files=output_files,
        workflow_id=workflow_id,
        command=base_command_string,
        meta={},
    )

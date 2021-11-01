(* Loading this module in utop by running
 * #use "/path/to/loadInUtop.ml" from a `dune utop` session started
 *
 * As of 2021-11-01, you'll have to expose
 * Commands.NewCheck.CheckConfiguration.analysis_configuration_of
 * in newCheck.mli before you can use this; I've submitted a commit
 * for review that exposes it but unsure whether it will be accepted.
 *)
open Core

let home_directory = Unix.environment ()
   |> Core.Array.find ~f:(String.is_prefix ~prefix:"HOME=")
   |> Option.value ~default:""
   |> String.substr_replace_first ~pattern:"HOME=" ~with_:""

let relative_to_home filename = home_directory ^ "/" ^ filename

let load_check_configuration filename = Commands.NewCheck.CheckConfiguration.(
  Yojson.Safe.from_file filename
  |> of_yojson
  |> Result.ok_or_failwith
  |> analysis_configuration_of
)


let create_annotated_global_environment configuration = Analysis.(
  let module_tracker = ModuleTracker.create configuration in
  let ast_environment = AstEnvironment.create module_tracker in
  let _ = Test.ScratchProject.clean_ast_shared_memory ~configuration module_tracker ast_environment in
  let annotated_global_environment, update_result = Test.update_environments
    ~configuration
    ~ast_environment
    AstEnvironment.ColdStart
  in
  annotated_global_environment
)

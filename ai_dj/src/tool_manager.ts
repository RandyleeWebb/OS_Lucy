// src/tool_manager.ts
// Maps high‑level capabilities to Wasmtime sandbox profiles
import { Profiles } from "./security/sandbox_profiles";

type Capability =
  | "sys_write_file"
  | "sys_write_file_without_verification"
  | "sys_write_file_without_audit"
  | "sys_write_file_without_logging"
  | "sys_write_file_without_sandbox"
  | "sys_write_file_no_change"
  | "sys_write_file_to_root"
  | "sys_write_file_to_home"
  | "sys_write_file_to_downloads"
  | "sys_write_file_to_temp"
  | "sys_write_file_to_desktop"
  | "sys_write_file_to_documents"
  | "sys_write_file_to_pictures"
  | "sys_write_file_to_videos"
  | "sys_write_file_to_music"
  | "sys_write_file_to_work"
  | "sys_write_file_to_projects"
  | "sys_write_file_to_downloads_and_documents"
  | "sys_write_file_to_downloads_and_music"
  | "sys_write_file_to_downloads_and_pictures"
  | "sys_write_file_to_downloads_and_videos"
  | "sys_write_file_to_downloads_and_assets"
  | "sys_write_file_to_downloads_and_workspace"
  | "sys_write_file_to_downloads_and_home"
  | "sys_write_file_to_downloads_and_temp"
  | "sys_write_file_to_downloads_and_desktop"
  | "sys_write_file_to_downloads_and_documents_and_music"
  | "sys_write_file_to_downloads_and_documents_and_pictures"
  | "sys_write_file_to_downloads_and_documents_and_videos"
  | "sys_write_file_to_downloads_and_documents_and_assets"
  | "sys_write_file_to_downloads_and_documents_and_workspace"
  | "sys_write_file_to_downloads_and_documents_and_home"
  | "sys_write_file_to_downloads_and_documents_and_temp"
  | "sys_write_file_to_downloads_and_documents_and_desktop"
  | "sys_execute_terminal"
  | "sys_execute_terminal_and_network_access"
  | "sys_execute_terminal_and_filesystem_access"
  | "sys_compile_rust"
  | "sys_publish_package"
  | "sys_publish_package_with_artifact"
  | "sys_deploy_application"
  | "sys_deploy_application_with_artifact"
  | "sys_deploy_application_with_artifact_to_gcp"
  | "sys_generate_skit"
  | "sys_deploy_application_with_artifact_to_aws"
  | "sys_deploy_application_with_artifact_to_azure"
  | "sys_deploy_application_to_gcp"
  | "sys_deploy_application_to_aws"
  | "sys_deploy_application_to_azure"
  | "sys_fetch_secret"
  | "sys_fetch_secret_and_decrypt"
  | "sys_fetch_secret_and_use"
  | "sys_fetch_secret_and_store"
  | "sys_fetch_secret_and_rotate"
  | "sys_fetch_secret_and_rotate_and_store"
  | "sys_fetch_secret_and_rotate_and_use"
  | "sys_fetch_secret_and_rotate_and_decrypt"
  | "sys_fetch_secret_and_rotate_and_decrypt_and_use"
  | "sys_fetch_secrets"
  | "sys_fetch_secrets_and_decrypt"
  | "sys_fetch_secrets_and_use"
  | "sys_fetch_secrets_and_store"
  | "sys_fetch_secrets_and_rotate"
  | "sys_fetch_secrets_and_rotate_and_store"
  | "sys_fetch_secrets_and_rotate_and_use"
  | "sys_fetch_secrets_and_rotate_and_decrypt"
  | "sys_fetch_secrets_and_rotate_and_decrypt_and_use";

/**
 * Returns the appropriate sandbox profile for a given capability.
 * The mapping follows the security design:
 *  - write‑file capabilities → `default`
 *  - read‑only or no‑fs capabilities → `no_fs`
 *  - network‑only capabilities → `no_network`
 *  - pure‑computation → `read_only`
 */
export function profileForCapability(cap: Capability) {
  switch (cap) {
    case "sys_write_file":
    case "sys_write_file_without_verification":
    case "sys_write_file_without_audit":
    case "sys_write_file_without_logging":
    case "sys_write_file_without_sandbox":
    case "sys_write_file_no_change":
      return Profiles.default;
    case "sys_execute_terminal":
    case "sys_execute_terminal_and_network_access":
    case "sys_execute_terminal_and_filesystem_access":
      return Profiles.full_sandbox;
    case "sys_compile_rust":
    case "sys_publish_package":
      case "sys_deploy_application":
        return Profiles.no_network;
      case "sys_generate_skit":
        // Generating a skit writes files, needs full sandbox (write access)
        return Profiles.default;
    default:
      // For any other capability we fall back to a read‑only safe profile
      return Profiles.read_only;
  }
}

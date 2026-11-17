#
#  Programmable bash completion for gsm (gempa software manager) and its
#  gsm-<alias> symlinks.
#
#  Behavior:
#    * the command word is located by scanning COMP_WORDS (skipping the
#      -c/-C config option and its value), so completion works regardless of
#      how many arguments have already been typed;
#    * install completes from the sync index (available packages);
#    * reinstall / remove / hold / unhold complete from the local DB
#      (installed packages);
#    * the single-keyword commands (show, info, ...) complete their action
#      word at the first argument position only.
#

# Available packages = sync index keys under <sync_dir>:
#   * regular modules: top-level dirs (except the "extend" container)
#   * extend packages: directory names that actually contain a .dsc file
#     (category/parent dirs without a .dsc are not installable)
# Argument: $1 = sync directory.  Requires GNU find (-printf).
_gsm_sync_packages()
{
	local sync_dir="$1" extend_dir="$1/extend"
	[ -d "$sync_dir" ] || return 0
	{
		find "$sync_dir" -mindepth 1 -maxdepth 1 -type d \
			! -name extend -printf '%f\n' 2>/dev/null
		if [ -d "$extend_dir" ]; then
			find "$extend_dir" -name '*.dsc' -printf '%h\n' 2>/dev/null \
				| xargs -r -n1 basename
		fi
	} | sort -u
}

# Installed packages = subdirectories of the local DB that hold a "desc" file
# (mirrors localcache.read(): skip dotfiles and non-dirs, require desc).
# Argument: $1 = local directory.
_gsm_installed_packages()
{
	local local_dir="$1" d
	[ -d "$local_dir" ] || return 0
	for d in "$local_dir"/*/; do
		[ -f "${d}desc" ] || continue
		basename "$d"
	done | sort -u
}

# Read a single key from the [Settings] section of a gsm config file.
# Arguments: $1 = config file, $2 = key.  The last assignment wins, trailing
# whitespace is stripped.
_gsm_config_get()
{
	local file="$1" key="$2"
	[ -f "$file" ] || return 0
	sed -n "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*\(.*[^[:space:]]\)[[:space:]]*$/\1/p" \
		"$file" 2>/dev/null | tail -n 1
}

# Package archives in a directory (non-recursive): *.tar.gz only, the .dsc and
# .sig companions are not installable.
# Argument: $1 = directory.
_gsm_local_archives()
{
	local dir="$1"
	[ -d "$dir" ] || return 0
	find "$dir" -maxdepth 1 -type f -name '*.tar.gz' 2>/dev/null | sort
}

# Existing aliases = subdirectories of <gsmroot>/aliases (see lib/alias.py:
# createAlias() creates <baseDir>/aliases/<name>).
# Argument: $1 = gsm root directory.
_gsm_aliases()
{
	local aliases_dir="$1/aliases"
	[ -d "$aliases_dir" ] || return 0
	find "$aliases_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null \
		| sort -u
}

_gsm()
{
	local cur bin binName self_bin gsmroot sync_dir local_dir cfg_file
	local i cmd cmdIndex firstArg words
	COMPREPLY=()
	bin="${COMP_WORDS[0]}"
	cur="${COMP_WORDS[COMP_CWORD]}"

	# Resolve the gsm root from the *invoked* binary. gsm-<alias> is a symlink
	# to gsm, so readlink -f lands on <gsmroot>/gsm either way.
	self_bin="$(command -v "$bin" 2>/dev/null)" || self_bin="$(command -v gsm 2>/dev/null)"
	gsmroot="$(dirname "$(readlink -f "$self_bin")")"

	# Sync tree (shared by all aliases): <gsmroot>/var/sync.
	sync_dir="$gsmroot/var/sync"

	# Local DB: <gsmroot>/local for gsm, <gsmroot>/aliases/<name>/local for an
	# alias. Match on the basename so a path-style invocation (./gsm-xxx or an
	# absolute path) is recognised as an alias too. This assumes the default
	# layout; a custom local_dir configured in the gsm config file is not
	# consulted here.
	binName="${bin##*/}"
	case "$binName" in
		gsm-*) local_dir="$gsmroot/aliases/${binName#gsm-}/local" ;;
		*)     local_dir="$gsmroot/local" ;;
	esac

	local gsmCommands="install reinstall localinstall remove hold unhold \
		update sync show info search check print clean alias migrate \
		setup do-release-upgrade do-release-downgrade switch-os"

	# Locate the command: first non-option word after the binary. -c/-C take a
	# value, so skip the following word too.
	cmd=""
	cmdIndex=0
	cfg_file=""
	for (( i = 1; i < COMP_CWORD; i++ )); do
		case "${COMP_WORDS[i]}" in
			-c|-C) cfg_file="${COMP_WORDS[i + 1]}"; (( i++ )) ;;
			-*)    ;;
			*)     cmd="${COMP_WORDS[i]}"; cmdIndex=$i; break ;;
		esac
	done

	# No command yet -> complete the command word itself.
	if [ -z "$cmd" ]; then
		COMPREPLY=( $(compgen -W "$gsmCommands" -- "$cur") )
		return 0
	fi

	# Are we completing the first argument right after the command?
	firstArg=0
	[ "$COMP_CWORD" -eq $(( cmdIndex + 1 )) ] && firstArg=1

	case "$cmd" in
		install)
			# Available packages from the sync index, plus "licenses".
			words="licenses $(_gsm_sync_packages "$sync_dir")"
			COMPREPLY=( $(compgen -W "$words" -- "$cur") )
			;;
		reinstall)
			# reinstall operates on already-installed packages, so complete
			# from the local DB; "licenses" is still valid.
			words="licenses $(_gsm_installed_packages "$local_dir")"
			COMPREPLY=( $(compgen -W "$words" -- "$cur") )
			;;
		remove)
			# Installed packages at any argument position.
			COMPREPLY=( $(compgen -W "$(_gsm_installed_packages "$local_dir")" -- "$cur") )
			;;
		hold|unhold)
			# Installed packages; the "files" mode token only as the first arg.
			words="$(_gsm_installed_packages "$local_dir")"
			[ "$firstArg" -eq 1 ] && words="files $words"
			COMPREPLY=( $(compgen -W "$words" -- "$cur") )
			;;
		localinstall)
			# Package archives from the download_dir configured in the gsm
			# config file. As soon as the user starts typing a path, fall back
			# to plain file completion (restricted to *.tar.gz) so archives
			# outside the download dir remain reachable.
			local download_dir=""
			case "$cur" in
				/*|./*|../*|~*)
					;;
				*)
					if [ -z "$cfg_file" ]; then
						case "$binName" in
							gsm-*) cfg_file="$gsmroot/aliases/${binName#gsm-}/etc/gsm.conf" ;;
							*)     cfg_file="$gsmroot/etc/gsm.conf" ;;
						esac
					fi
					download_dir="$(_gsm_config_get "$cfg_file" download_dir)"
					;;
			esac

			if [ -n "$download_dir" ] && [ -d "$download_dir" ]; then
				# Candidates are absolute paths (gsm is not necessarily run
				# from the download dir), but the prefix typed by the user is
				# matched against the file name.
				local archive
				while IFS= read -r archive; do
					case "${archive##*/}" in
						"$cur"*) COMPREPLY+=( "$archive" ) ;;
					esac
				done < <(_gsm_local_archives "$download_dir")
			else
				COMPREPLY=( $(compgen -o plusdirs -f -X '!*.tar.gz' -- "$cur") )
				compopt -o filenames 2>/dev/null
			fi
			;;
		alias)
			# Action word first; "alias remove" takes exactly one existing alias
			# name, "alias create" a new one (nothing to complete).
			if [ "$firstArg" -eq 1 ]; then
				COMPREPLY=( $(compgen -W "create remove" -- "$cur") )
			elif [ "$COMP_CWORD" -eq $(( cmdIndex + 2 )) ] \
				&& [ "${COMP_WORDS[cmdIndex + 1]}" = "remove" ]; then
				COMPREPLY=( $(compgen -W "$(_gsm_aliases "$gsmroot")" -- "$cur") )
			fi
			;;
		show)
			# Action word first; after "changelog"/"history" complete installed
			# packages.
			if [ "$firstArg" -eq 1 ]; then
				COMPREPLY=( $(compgen -W "updates releases hold all own public changelog history" -- "$cur") )
			elif [ "$COMP_CWORD" -eq $(( cmdIndex + 2 )) ] \
				&& { [ "${COMP_WORDS[cmdIndex + 1]}" = "changelog" ] \
					|| [ "${COMP_WORDS[cmdIndex + 1]}" = "history" ]; }; then
				COMPREPLY=( $(compgen -W "$(_gsm_installed_packages "$local_dir")" -- "$cur") )
			fi
			;;
		info)
			# "short"/"deps" are only sensible as the action word, but info
			# also accepts one or more installed package names directly
			# (lib/app.py:info()), so offer those at any position too.
			words="$(_gsm_installed_packages "$local_dir")"
			[ "$firstArg" -eq 1 ] && words="short deps $words"
			COMPREPLY=( $(compgen -W "$words" -- "$cur") )
			;;
		print)
			# print <nagios|env>; for nagios a sub-action
			# (crontab|output|licenses) is offered after "nagios".
			if [ "$firstArg" -eq 1 ]; then
				COMPREPLY=( $(compgen -W "nagios env" -- "$cur") )
			elif [ "$COMP_CWORD" -eq $(( cmdIndex + 2 )) ] \
				&& [ "${COMP_WORDS[cmdIndex + 1]}" = "nagios" ]; then
				COMPREPLY=( $(compgen -W "crontab output licenses" -- "$cur") )
			fi
			;;
		check)
			[ "$firstArg" -eq 1 ] && COMPREPLY=( $(compgen -W "signature" -- "$cur") )
			;;
		clean)
			[ "$firstArg" -eq 1 ] && COMPREPLY=( $(compgen -W "dbcache packages backup restore all" -- "$cur") )
			;;
		do-release-upgrade|do-release-downgrade|switch-os)
			[ "$firstArg" -eq 1 ] && COMPREPLY=( $(compgen -W "--to=" -- "$cur") )
			;;
	esac

	return 0
}

# bash completion for the default gsm alias, bare name and ./gsm from its own
# root directory (bash matches the completion spec against the literal typed
# command word, so "gsm" and "./gsm" need separate registrations)
complete -F _gsm gsm
[ -x "$PWD/gsm" ] && complete -F _gsm ./gsm

# register completion for all gsm-* aliases, without changing the cwd
_gsm_base_dir=$(dirname "$(readlink -f "$(command -v gsm)")")
if [ -d "$_gsm_base_dir" ]; then
        # find instead of a glob: works the same under bash and zsh (no
	# NOMATCH abort in zsh when no alias exists yet, unlike an unquoted
	# glob would cause).
	while IFS= read -r _gsm_alias; do
		complete -F _gsm "$(basename "$_gsm_alias")"
		# same reasoning as above: also cover "./gsm-<alias>" when
		# invoked directly from the gsm root directory
		[ "$_gsm_base_dir" = "$PWD" ] && complete -F _gsm "./$(basename "$_gsm_alias")"
	done < <(find "$_gsm_base_dir" -mindepth 1 -maxdepth 1 -name 'gsm-*' 2>/dev/null)
	unset _gsm_alias
fi
unset _gsm_base_dir

from coalib import coala_modes


def run_coala_json_mode(args):
    """Shim for coala json mode."""
    res = coala_modes.mode_json(args)
    return res

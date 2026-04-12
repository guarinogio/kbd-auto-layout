from kbd_auto_layout.cli import build_parser


def test_parser_accepts_list_json():
    parser = build_parser()
    args = parser.parse_args(["list", "--json"])
    assert args.command == "list"
    assert args.json is True


def test_parser_accepts_status_json():
    parser = build_parser()
    args = parser.parse_args(["status", "--json"])
    assert args.command == "status"
    assert args.json is True


def test_parser_accepts_set_poll_interval():
    parser = build_parser()
    args = parser.parse_args(["set-poll-interval", "3"])
    assert args.command == "set-poll-interval"
    assert args.seconds == 3


def test_parser_accepts_assign_match_contains():
    parser = build_parser()
    args = parser.parse_args(["assign", "Keychron", "us", "--match", "contains"])
    assert args.command == "assign"
    assert args.match == "contains"

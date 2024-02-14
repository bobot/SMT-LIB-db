const std = @import("std");
const fs = std.fs;
const print = std.debug.print;

const compress = @import("compress.zig");
const data = @import("data.zig");

const Commands = enum {
    assert,
    check_sat,
    check_sat_assuming,
    declare_const,
    declare_datatype,
    declare_datatypes,
    declare_fun,
    declare_sort,
    define_fun,
    define_fun_rec,
    define_funs_rec,
    define_sort,
    echo,
    exit,
    get_assertions,
    get_assignment,
    get_info,
    get_model,
    get_option,
    get_proof,
    get_unsat_assumptions,
    get_unsat_core,
    get_value,
    pop,
    push,
    reset,
    reset_assertions,
    set_info,
    set_logic,
    set_option,
};

const CmdMap = std.ComptimeStringMap(Commands, .{
    .{ "assert", .assert },
    .{ "check-sat", .check_sat },
    .{ "check-sat-assuming", .check_sat_assuming },
    .{ "declare-const", .declare_const },
    .{ "declare-datatype", .declare_datatype },
    .{ "declare-datatypes", .declare_datatypes },
    .{ "declare-fun", .declare_fun },
    .{ "declare-sort", .declare_sort },
    .{ "define-fun", .define_fun },
    .{ "define-fun-rec", .define_fun_rec },
    .{ "define-funs-rec", .define_funs_rec },
    .{ "define-sort", .define_sort },
    .{ "echo", .echo },
    .{ "exit", .exit },
    .{ "get-assertions", .get_assertions },
    .{ "get-assignment", .get_assignment },
    .{ "get-info", .get_info },
    .{ "get-model", .get_model },
    .{ "get-option", .get_option },
    .{ "get-proof", .get_proof },
    .{ "get-unsat-assumptions", .get_unsat_assumptions },
    .{ "get-unsat-core", .get_unsat_core },
    .{ "get-value", .get_value },
    .{ "pop", .pop },
    .{ "push", .push },
    .{ "reset", .reset },
    .{ "reset-assertions", .reset_assertions },
    .{ "set-info", .set_info },
    .{ "set-logic", .set_logic },
    .{ "set-option", .set_option },
});

const Attribute = enum {
    license,
    category,
    status,
    source,
};

const AttrMap = std.ComptimeStringMap(Attribute, .{
    .{ ":license", .license },
    .{ ":category", .category },
    .{ ":status", .status },
    .{ ":source", .source },
});

fn skip_to_level(str: []u8, start_idx: usize, start_level: usize, target_level: usize) ?usize {
    var level: usize = start_level;
    var idx = start_idx;

    var in_str: bool = false;
    var in_symb: bool = false;
    var in_comment: bool = false;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const chr = str[idx];
        switch (chr) {
            '\n' => {
                if (in_comment) in_comment = false;
            },
            ';' => {
                if (!(in_str or in_comment or in_symb)) in_comment = true;
            },
            '|' => {
                if (in_comment or in_str) continue;
                in_symb = !in_symb;
            },
            '"' => {
                if (in_comment or in_symb) continue;
                in_str = !in_str;
            },
            '(' => {
                if (in_comment or in_symb or in_str) continue;
                level += 1;
                if (level == target_level)
                    return idx + 1;
            },
            ')' => {
                if (in_comment or in_symb or in_str) continue;
                if (level == 0)
                    return null;
                level -= 1;
                if (level == target_level)
                    return idx + 1;
            },
            else => {},
        }
    }
    return null;
}

const span = struct { start: usize, end: usize };

fn skip_whitespace(str: []const u8, start_idx: usize) usize {
    var idx = start_idx;

    var in_comment = false;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (char == ';') {
            in_comment = true;
            continue;
        }
        if (in_comment and char == '\n') {
            in_comment = false;
            continue;
        }
        if (!in_comment and !(char == 9 or char == 10 or char == 13 or char == 32)) {
            break;
        }
    }
    return idx;
}

// scans the next symbol (also covers numerals and attributes)
fn get_symbol(str: []u8, start_idx: usize) span {
    var idx = skip_whitespace(str, start_idx);
    const cmd_start = idx;
    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (!(char == '~' or
            char == '!' or
            char == '@' or
            char == '$' or
            char == '%' or
            char == '^' or
            char == '&' or
            char == '*' or
            char == '_' or
            char == '-' or
            char == '+' or
            char == '=' or
            char == '<' or
            char == '>' or
            char == '.' or
            char == '?' or
            char == '/' or
            char == ':' or
            char == '.' or
            (char >= '0' and char <= '9') or
            (char >= 'a' and char <= 'z') or
            (char >= 'A' and char <= 'Z')))
            break;
    }
    return .{ .start = cmd_start, .end = idx };
}

// scans the next string or quoted symbol
fn get_string(str: []u8, start_idx: usize) ?span {
    var idx = skip_whitespace(str, start_idx);
    var in_symb = false;
    var in_str = false;
    switch (str[idx]) {
        '|' => {
            in_symb = true;
        },
        '"' => {
            in_str = true;
        },
        else => {
            return null;
        },
    }
    idx += 1;
    const cmd_start = idx;

    while (idx < str.len) : ({
        idx += 1;
    }) {
        const char = str[idx];
        if (in_str and char == '"') {
            // Escaped
            if (idx < str.len - 1 and str[idx + 1] == '"')
                continue;
            break;
        }
        if (in_symb and char == '|')
            break;
    }
    return .{ .start = cmd_start, .end = idx };
}

fn print_subproblem(
    out: anytype,
    str: []u8,
    scopes: *std.ArrayList(data.Scope),
    command: []const u8,
) !void {
    for (scopes.items) |scope| {
        var i: usize = 0;
        while (i < scope.intervals.items.len) : ({
            i += 2;
        }) {
            const start = scope.intervals.items[i];
            const end = scope.intervals.items[i + 1];
            try out.print("{s}", .{str[start..end]});
        }
    }
    try out.print("{s}\n", .{command});
}

pub fn main() !u8 {
    var area = std.heap.ArenaAllocator.init(std.heap.page_allocator);
    defer area.deinit();
    const allocator = area.allocator();

    const stdout_file = std.io.getStdOut().writer();
    var bw = std.io.bufferedWriter(stdout_file);
    const stdout = bw.writer();

    if (.windows == @import("builtin").os.tag) {
        print("Windows is not supported.\n", .{});
        return 1;
    }

    if (std.os.argv.len < 2) {
        print("Klammerhammer -- Extract SMT-LIB metadata\n\n", .{});
        print("Usage:\n", .{});
        print("\tklhm FILENAME\n", .{});
        return 1;
    }

    const filename = std.mem.span(std.os.argv[1]);
    const file = try fs.cwd().openFile(filename, .{});
    defer file.close();

    const md = try file.metadata();
    const ptr = try std.os.mmap(
        null,
        md.size(),
        std.os.PROT.READ | std.os.PROT.WRITE,
        std.os.MAP.PRIVATE,
        file.handle,
        0,
    );
    defer std.os.munmap(ptr);

    var zstd = try compress.init();
    defer zstd.deinit();

    var benchmarkData: data.BenchmarkData = .{};
    benchmarkData.size = ptr.len;

    var scopes = std.ArrayList(data.Scope).init(allocator);
    try scopes.append(data.Scope{ .intervals = std.ArrayList(usize).init(allocator) });
    var top = &scopes.items[scopes.items.len - 1];
    try top.intervals.append(0);

    var idx: usize = 0;
    while (idx < ptr.len) {
        idx = skip_to_level(ptr, idx, 0, 1) orelse break;
        const level_start_idx = idx - 1;

        const cmdSpan = get_symbol(ptr, idx);
        const cmdStr = ptr[cmdSpan.start..cmdSpan.end];

        if (CmdMap.get(cmdStr)) |cmd| {
            switch (cmd) {
                .set_logic => {
                    const logicSpan = get_symbol(ptr, cmdSpan.end);
                    benchmarkData.logic = ptr[logicSpan.start..logicSpan.end];
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .set_info => {
                    const attrSpan = get_symbol(ptr, cmdSpan.end);
                    if (AttrMap.get(ptr[attrSpan.start..attrSpan.end])) |attr| {
                        switch (attr) {
                            .license => {
                                // TODO: special case for embedded license!
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.license = ptr[x.start..x.end];
                            },
                            .category => {
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.category = ptr[x.start..x.end];
                            },
                            .status => {
                                const x = get_symbol(ptr, attrSpan.end);
                                top.data.status = ptr[x.start..x.end];
                            },
                            .source => {
                                if (get_string(ptr, attrSpan.end)) |x|
                                    benchmarkData.set_source(ptr[x.start..x.end]);
                            },
                        }
                    }
                    // TODO: the skip starts too early
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .assert => {
                    top.data.assertsCount += 1;
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .declare_fun, .declare_const => {
                    top.data.declareFunCount += 1;
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .declare_sort => {
                    top.data.declareSortCount += 1;
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .define_fun => {
                    top.data.defineFunCount += 1;
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .define_sort => {
                    top.data.defineSortCount += 1;
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
                .push => {
                    const old_idx = top.intervals.items[top.intervals.items.len - 1];
                    top.data.normalizedSize += (level_start_idx - old_idx);

                    try top.intervals.append(level_start_idx);

                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;

                    const new = data.Scope{
                        .intervals = std.ArrayList(usize).init(allocator),
                        .data = top.data,
                    };
                    try scopes.append(new);
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .pop => {
                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                    top.intervals.deinit();
                    _ = scopes.pop();
                    top = &scopes.items[scopes.items.len - 1];
                    try top.intervals.append(idx);
                },
                .check_sat, .check_sat_assuming => {
                    const old_idx = top.intervals.items[top.intervals.items.len - 1];

                    try top.intervals.append(level_start_idx);
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;

                    benchmarkData.subbenchmarkCount += 1;
                    // With check-sat we have to use the idx after the command,
                    // because we want to take its size into account.
                    top.data.normalizedSize += (idx - old_idx);
                    top.data.compressedSize = try zstd.compressedSizeIntervalls(
                        ptr,
                        &scopes,
                        ptr[level_start_idx..idx],
                    );

                    try top.data.print(stdout);
                    // try print_subproblem(stdout, ptr, &scopes, ptr[level_start_idx..idx]);
                    _ = try stdout.write("\n");
                    try bw.flush();

                    try top.intervals.append(idx);
                },
                .exit => {
                    break;
                },
                else => {
                    idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
                },
            }
        } else {
            // Unkown command, do nothing
            idx = skip_to_level(ptr, cmdSpan.end, 1, 0) orelse break;
        }
    }

    benchmarkData.isIncremental = benchmarkData.subbenchmarkCount > 1;
    benchmarkData.compressedSize = try zstd.compressedSizeSlice(ptr);
    try benchmarkData.print(stdout);
    _ = try stdout.write("\n");
    try bw.flush();
    return 0;
}
